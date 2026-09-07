"""Local authentication and role authorization for SAD and Forge."""

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
import threading

from runtime_document import RuntimeJSONDocument

PASSWORD_ITERATIONS = 600_000
SESSION_HOURS = 12
MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 15
MAX_ACCOUNTS_FILE_BYTES = 2_000_000
MAX_ACCOUNTS = 500
MAX_SESSIONS_PER_ACCOUNT = 10
MAX_TOTAL_SESSIONS = 1_000
ACCOUNTS_NAMESPACE = "accounts"
ACCOUNTS_FILENAME = "accounts.json"

class Role(str, Enum):
    STUDENT="student"; TEACHER="teacher"; OWNER="owner"; DEVELOPER="developer"; REVIEWER="reviewer"; VIEWER="viewer"

ROLE_PERMISSIONS={
 Role.STUDENT.value:{"study:personal","forge:play","progress:own"},
 Role.TEACHER.value:{"study:personal","forge:play","progress:own","progress:students","account:create_student"},
 Role.DEVELOPER.value:{"study:personal","development:view","development:work","development:work_assigned"},
 Role.REVIEWER.value:{"development:view","development:review","development:decide"},
 Role.VIEWER.value:{"development:view"},
 Role.OWNER.value:{"study:personal","forge:play","progress:own","progress:students","account:create_student","account:create_teacher","account:create_developer","account:create_reviewer","account:create_viewer","account:list","account:manage","platform:manage","development:view","development:review","development:work","development:work_assigned","development:decide","development:govern"},
}

def _now(): return datetime.now(timezone.utc)
def _normalized_username(username):
    if not isinstance(username,str): raise ValueError("Username must be text.")
    value=username.strip().lower()
    if not 3<=len(value)<=64 or not all(c.isalnum() or c in ".-_" for c in value): raise ValueError("Username must be 3-64 characters using letters, numbers, dot, dash, or underscore.")
    return value

def _validate_password(password):
    if not isinstance(password,str) or not 12<=len(password)<=1024: raise ValueError("Password must be 12-1024 characters.")
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password): raise ValueError("Password must contain at least one letter and one number.")

def _password_hash(password,salt=None):
    salt_bytes=secrets.token_bytes(16) if salt is None else bytes.fromhex(salt)
    digest=hashlib.pbkdf2_hmac("sha256",password.encode("utf-8"),salt_bytes,PASSWORD_ITERATIONS)
    return salt_bytes.hex(),digest.hex()

def _validate_accounts_data(data):
    if not isinstance(data,dict) or data.get("schema_version")!=1 or not isinstance(data.get("accounts"),list): raise ValueError("Unsupported or invalid accounts data.")
    if len(data["accounts"])>MAX_ACCOUNTS: raise ValueError("Accounts data exceeds the installation account limit.")
    seen_ids=set(); seen_users=set()
    for account in data["accounts"]:
        if not isinstance(account,dict): raise ValueError("Invalid account record.")
        if account.get("role") not in ROLE_PERMISSIONS: raise ValueError("Account record contains an unsupported role.")
        aid=account.get("account_id"); username=account.get("username")
        if not isinstance(aid,str) or not aid or aid in seen_ids: raise ValueError("Account IDs must be unique non-empty strings.")
        if not isinstance(username,str) or not username or username in seen_users: raise ValueError("Account usernames must be unique non-empty strings.")
        if not isinstance(account.get("password_salt"),str) or not isinstance(account.get("password_hash"),str): raise ValueError("Account password verifier data is invalid.")
        seen_ids.add(aid); seen_users.add(username)
    return data

class AuthService:
    def __init__(self,accounts_file=None,now=None,database=None):
        self.now=now or _now
        self.persistence=RuntimeJSONDocument(ACCOUNTS_FILENAME,ACCOUNTS_NAMESPACE,{"schema_version":1,"accounts":[]},_validate_accounts_data,MAX_ACCOUNTS_FILE_BYTES,path=accounts_file,database=database)
        self.accounts_file=self.persistence.path; self.sessions={}; self.lock=threading.RLock()
    def _load(self): return self.persistence.load()
    def _save(self,data): self.persistence.save(data)
    def _prune_sessions(self,now=None):
        now=now or self.now(); self.sessions={k:v for k,v in self.sessions.items() if v.get("expires_at") and now<v["expires_at"]}
    @staticmethod
    def _session_order(item): return item[1].get("created_at") or item[1].get("expires_at")
    def _make_session_room(self,account_id,now):
        self._prune_sessions(now); items=sorted(((k,v) for k,v in self.sessions.items() if v.get("account_id")==account_id),key=self._session_order)
        while len(items)>=MAX_SESSIONS_PER_ACCOUNT: self.sessions.pop(items.pop(0)[0],None)
        while len(self.sessions)>=MAX_TOTAL_SESSIONS: self.sessions.pop(min(self.sessions.items(),key=self._session_order)[0],None)
    def has_owner(self): return any(a.get("role")==Role.OWNER.value for a in self._load()["accounts"])
    def _find(self,data,username): return next((a for a in data["accounts"] if a["username"]==username),None)
    def bootstrap_owner(self,username,password,explicitly_approved=False):
        with self.lock:
            if not explicitly_approved: raise PermissionError("Explicit approval is required to bootstrap an owner.")
            data=self._load()
            if any(a["role"]==Role.OWNER.value for a in data["accounts"]): raise PermissionError("An owner already exists.")
            return self._create(data,username,password,Role.OWNER.value)
    def create_account(self,username,password,role,actor_token):
        with self.lock:
            role_value=Role(role).value; actor=self.require(actor_token)
            required={Role.STUDENT.value:"account:create_student",Role.TEACHER.value:"account:create_teacher",Role.DEVELOPER.value:"account:create_developer",Role.REVIEWER.value:"account:create_reviewer",Role.VIEWER.value:"account:create_viewer",Role.OWNER.value:None}[role_value]
            if required is None or required not in ROLE_PERMISSIONS[actor["role"]]: raise PermissionError("The signed-in account cannot create that role.")
            return self._create(self._load(),username,password,role_value)
    def create_invited_student(self,username,password):
        """Provision only a student after the signup-invite service has authorized enrollment."""
        with self.lock: return self._create(self._load(),username,password,Role.STUDENT.value)
    def _create(self,data,username,password,role):
        normalized=_normalized_username(username); _validate_password(password)
        if len(data["accounts"])>=MAX_ACCOUNTS: raise ValueError("Account limit reached for this Alpha installation.")
        if self._find(data,normalized): raise ValueError("That username already exists.")
        salt,password_hash=_password_hash(password)
        account={"account_id":str(uuid.uuid4()),"username":normalized,"role":role,"password_salt":salt,"password_hash":password_hash,"created_at":self.now().isoformat(),"active":True,"failed_attempts":0,"locked_until":None,"profile":{"display_name":normalized,"level":0}}
        data["accounts"].append(account); self._save(data); return self.public_account(account)
    def login(self,username,password):
        with self.lock:
            normalized=_normalized_username(username); data=self._load(); account=self._find(data,normalized)
            if not account:return None
            now=self.now(); locked_until=datetime.fromisoformat(account["locked_until"]) if account.get("locked_until") else None
            if locked_until and now<locked_until:return None
            _,candidate=_password_hash(password,account["password_salt"]); valid=account.get("active",False) and hmac.compare_digest(candidate,account["password_hash"])
            if not valid:
                account["failed_attempts"]=account.get("failed_attempts",0)+1
                if account["failed_attempts"]>=MAX_FAILED_ATTEMPTS: account["locked_until"]=(now+timedelta(minutes=LOCK_MINUTES)).isoformat(); account["failed_attempts"]=0
                self._save(data); return None
            account["failed_attempts"]=0; account["locked_until"]=None; self._save(data); self._make_session_room(account["account_id"],now)
            token=secrets.token_urlsafe(32); self.sessions[token]={"account_id":account["account_id"],"created_at":now,"expires_at":now+timedelta(hours=SESSION_HOURS)}; return token
    def require(self,token,permission=None):
        session=self.sessions.get(token)
        if not session or self.now()>=session["expires_at"]: self.sessions.pop(token,None); raise PermissionError("A valid login session is required.")
        account=next((i for i in self._load()["accounts"] if i["account_id"]==session["account_id"] and i.get("active")),None)
        if not account: raise PermissionError("That account is unavailable.")
        if permission and permission not in ROLE_PERMISSIONS[account["role"]]: raise PermissionError("That role does not have the required permission.")
        return self.public_account(account)
    def logout(self,token): return self.sessions.pop(token,None) is not None
    def list_accounts(self,token): self.require(token,"account:list"); return [self.public_account(a) for a in self._load()["accounts"]]
    def list_students(self,token): self.require(token,"progress:students"); return [self.public_account(a) for a in self._load()["accounts"] if a["role"]==Role.STUDENT.value and a.get("active")]
    def set_account_active(self,account_id,active,token):
        actor=self.require(token,"account:manage")
        if not isinstance(active,bool): raise ValueError("Active must be true or false.")
        with self.lock:
            data=self._load(); account=next((i for i in data["accounts"] if i["account_id"]==account_id),None)
            if not account: raise KeyError("Account not found.")
            if account["role"]==Role.OWNER.value or account["account_id"]==actor["account_id"]: raise PermissionError("Owner accounts cannot be disabled through this endpoint.")
            account["active"]=active; self._save(data)
            if not active:self.sessions={k:v for k,v in self.sessions.items() if v["account_id"]!=account_id}
            return self.public_account(account)
    def change_password(self,token,current_password,new_password):
        actor=self.require(token); _validate_password(new_password)
        with self.lock:
            data=self._load(); account=next(i for i in data["accounts"] if i["account_id"]==actor["account_id"]); _,candidate=_password_hash(current_password,account["password_salt"])
            if not hmac.compare_digest(candidate,account["password_hash"]): raise PermissionError("Current password is incorrect.")
            salt,digest=_password_hash(new_password); account["password_salt"],account["password_hash"]=salt,digest; self._save(data); self.sessions={token:self.sessions[token]}; return True
    def get_profile(self,token):
        account=self.require(token); stored=next(i for i in self._load()["accounts"] if i["account_id"]==account["account_id"]); profile=stored.get("profile",{}); display=profile.get("display_name",account["username"]); level=profile.get("level",0)
        return {"display_name":display if isinstance(display,str) and display.strip() else account["username"],"level":level if level in {0,1,2} else 0}
    def update_profile(self,token,display_name=None,level=None):
        account=self.require(token); data=self._load(); stored=next(i for i in data["accounts"] if i["account_id"]==account["account_id"]); profile=stored.setdefault("profile",{"display_name":account["username"],"level":0})
        if display_name is not None:
            if not isinstance(display_name,str) or not display_name.strip() or len(display_name.strip())>80: raise ValueError("Display name must be 1-80 characters.")
            profile["display_name"]=display_name.strip()
        if level is not None:
            if level not in {0,1,2}: raise ValueError("Dialogue level must be 0, 1, or 2.")
            profile["level"]=level
        self._save(data); return dict(profile)
    @staticmethod
    def public_account(account): return {k:account[k] for k in ("account_id","username","role","created_at","active")}
