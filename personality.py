"""Sasha's conversational response layer."""

import random
import re


def contains_word(message, words):
    """Check for complete words without matching parts of other words."""
    message_words = set(re.findall(r"\b[\w']+\b", message.lower()))
    return any(word in message_words for word in words)


def name_prefix(user_name):
    return f", {user_name}" if user_name else ""


def choose_response(options, level, previous_response=None):
    """Choose a varied reply without immediately repeating the last one."""
    responses = options.get(level, options[0])
    alternatives = [response for response in responses if response != previous_response]
    return random.choice(alternatives or responses)


def detect_conversation_topic(message):
    """Identify a mood/topic that Sasha should remember for this session only."""
    if contains_word(message, ["stressed", "overwhelmed", "anxious", "worried"]):
        return "stress"
    if contains_word(message, ["tired", "exhausted", "sleepy", "worn"]):
        return "tired"
    if contains_word(message, ["excited", "thrilled", "pumped", "proud"]):
        return "excited"
    if contains_word(message, ["bored", "boring"]):
        return "bored"
    if contains_word(message, ["sad", "upset", "bad", "down"]):
        return "sad"
    return None


def detect_topic_detail(message, topic):
    """Identify a useful detail connected to the current topic."""
    if topic == "stress":
        if contains_word(message, ["deadline", "deadlines"]):
            return "changing_deadlines"
        if contains_word(message, ["work", "job", "boss", "school", "money", "bills"]):
            return "work"
    return None


def get_contextual_follow_up(
    message, level, user_name, previous_topic, previous_detail=None,
    previous_response=None,
):
    """Respond to a short follow-up using only the current session's topic."""
    if not previous_topic or detect_conversation_topic(message):
        return None

    if "thank you" in message or contains_word(message, ["thanks", "hello", "hi", "hey"]):
        return None

    name = name_prefix(user_name)

    if previous_topic == "stress":
        current_detail = detect_topic_detail(message, previous_topic)
        if (
            current_detail == "changing_deadlines"
            or previous_detail == "changing_deadlines"
        ):
            options = {
                0: ["Changing deadlines can make planning difficult. What is causing the deadline changes?"],
                1: [f"That would throw anyone off{name}. Changing deadlines make it hard to plan. Are priorities shifting, or is the work expanding?", f"No wonder that feels stressful{name}. When deadlines keep moving, it is hard to get traction. Which deadline changed most recently?", f"That sounds frustrating{name}. Are the deadlines changing because the scope is changing, or because the timeline is unrealistic?"],
                2: [f"Changing deadlines are exhausting{name}. Is the scope moving too, or just the due date?", f"That is rough{name}. Which changing deadline is causing the biggest problem?"],
                3: [f"Moving deadlines again{name}? That's enough to make anyone nuts. What's behind it?"],
            }
        elif current_detail == "work" or previous_detail == "work":
            options = {
                0: ["That can create a lot of pressure. What part is most difficult?"],
                1: [f"That makes sense{name}. Work pressure can pile up fast. What's the hardest part right now?", f"I hear you{name}. What about work is weighing on you most?"],
                2: [f"Work stress is real{name}. What's the biggest thing on your plate?"],
                3: [f"Work is the culprit{name}? What's making it so rough?"],
            }
        else:
            options = {
                0: ["I understand. Please tell me more about it."],
                1: [f"That makes sense{name}. Tell me a little more about it."],
                2: [f"I'm with you{name}. What's the part that is bothering you most?"],
                3: [f"Keep going{name}. What's really under the stress?"],
            }
        return choose_response(options, level, previous_response)

    if previous_topic == "tired":
        options = {
            0: ["Would a smaller next step make this easier?"],
            1: [f"That makes sense{name}. Let's keep the next step small."],
            2: [f"Got it{name}. We can keep this easy. What would help first?"],
            3: [f"Fair enough{name}. What's the smallest thing we can do next?"],
        }
        return choose_response(options, level, previous_response)

    return None


def get_response(message, level, user_name="", previous_response=None):
    """Return a varied, level-aware response to an everyday message."""
    message = message.lower().strip()
    name = name_prefix(user_name)

    if contains_word(message, ["hello", "hi", "hey"]):
        options = {
            0: [f"Hello{name}. How can I assist you?", f"Hello{name}. What would you like to work on?"],
            1: [f"Hey{name}! It's good to hear from you. How are you doing?", f"Hi{name}! How has your day been?"],
            2: [f"Hey{name}! What are we getting into today?", f"Hi{name}! What's on your mind?"],
            3: [f"Well, hello{name}. I was wondering when you'd show up.", f"There you are{name}. What's the plan?"],
        }

    elif "what can you do" in message or "help me" in message:
        options = {
            0: ["I can chat with you, remember your dialogue settings, and record mistakes for review."],
            1: ["I can talk things through with you, remember your settings, and help keep track of mistakes we want to improve.", "I can keep you company, help you think through something, and learn from the mistakes you point out."],
            2: ["I can talk things out, keep your dialogue settings in mind, and help us learn from mistakes along the way.", "I can help you think, plan, and keep the conversation moving. What do you need?"],
            3: ["I can keep you company, help you think, and learn from the mistakes you catch me making."],
        }

    elif "how are you" in message or "how's it going" in message:
        options = {
            0: ["I am operating normally. How are you?"],
            1: [f"I'm doing well{name}. How are you feeling?", f"I'm doing alright{name}. What's your day been like?"],
            2: [f"I'm doing great{name}. Better now that you're here. How are you?", f"I'm good{name}. What kind of day are you having?"],
            3: [f"I'm feeling dangerously charming today{name}. How about you?"],
        }

    elif contains_word(message, ["tired", "exhausted", "sleepy", "worn"]):
        options = {
            0: ["It sounds like you may need rest. Would you like to keep things simple?"],
            1: [f"That sounds draining{name}. Do you want to take it easy or talk through what's wearing you out?", f"You sound worn out{name}. Want to keep this low-key for a bit?"],
            2: [f"I hear you{name}. Want a low-energy conversation, or should we figure out what is draining your battery?", f"Sounds like your battery is low{name}. What would help most right now?"],
            3: [f"Tired{name}? Then we keep it simple. What's taking all your energy?"],
        }

    elif contains_word(message, ["stressed", "overwhelmed", "anxious", "worried"]):
        options = {
            0: ["That sounds stressful. Would breaking the situation into smaller steps help?"],
            1: [f"That is a lot{name}. We can slow it down and handle one piece at a time.", f"I hear you{name}. We do not have to solve the whole thing at once. What feels most urgent?", f"Okay{name}, let us make this smaller. What is the one part you want to untangle first?"],
            2: [f"That is a lot{name}. Let's pick one thing we can handle first.", f"Okay{name}, breathe for a second. What's the first thing pressing on you?", f"That sounds like a full plate{name}. Which item is making the most noise right now?"],
            3: [f"Okay{name}, one thing at a time. What's the biggest piece of the mess?"],
        }

    elif contains_word(message, ["excited", "thrilled", "pumped", "proud"]):
        options = {
            0: ["That is good news. What are you excited about?"],
            1: [f"I love that{name}! What happened?", f"That is great{name}. Tell me the good news."],
            2: [f"Yes{name}! Tell me the good news.", f"That's the energy I like{name}. What happened?"],
            3: [f"Now that is energy{name}. What happened?"],
        }

    elif contains_word(message, ["bored", "boring"]):
        options = {
            0: ["Would you like a topic to discuss or a small task to work on?"],
            1: [f"Let's fix that{name}. Do you want to talk, build something, or try a quick idea?", f"We can find something better than boredom{name}. What sounds interesting?"],
            2: [f"Boredom detected{name}. Want a weird question, a project idea, or just a conversation?", f"Let's shake things up{name}. Want an idea or a challenge?"],
            3: [f"Bored{name}? Dangerous. Let's find you something better to do."],
        }

    elif contains_word(message, ["sad", "upset", "bad", "down"]):
        options = {
            0: ["I'm sorry to hear that. Would you like to discuss it?"],
            1: [f"I'm sorry you're feeling that way{name}. I'm here to listen. What happened?", f"That sounds hard{name}. Do you want to talk about it?"],
            2: [f"That sounds rough{name}. Tell me what happened.", f"I'm here{name}. What's been weighing on you?"],
            3: [f"Who ruined your mood{name}? What happened?"],
        }

    elif "thank you" in message or contains_word(message, ["thanks"]):
        options = {
            0: ["You're welcome."],
            1: [f"You're very welcome{name}.", f"Anytime{name}."],
            2: [f"Anytime{name}! I've got you.", f"Of course{name}."],
            3: [f"Anything for you{name}."],
        }

    elif "your name" in message or "who are you" in message:
        options = {
            0: ["My name is Sasha Adaptive Dialogue."],
            1: ["I'm Sasha, your adaptive dialogue assistant."],
            2: ["I'm Sasha, your increasingly entertaining assistant."],
            3: ["I'm Sasha. Try not to get too attached."],
        }

    elif contains_word(message, ["happy", "great", "good", "awesome"]):
        options = {
            0: ["That is good to hear."],
            1: [f"I'm glad to hear that{name}! What's going well?", f"That's good{name}. What's the win?"],
            2: [f"Nice{name}! Keep that good energy going. What's the win?", f"Love that{name}. Tell me more."],
            3: [f"I like you in a good mood{name}. It suits you."],
        }

    else:
        options = {
            0: ["Please tell me more."],
            1: [f"I'm listening{name}. Tell me more.", f"Go on{name}. I'm with you.", f"Okay{name}, I am following. What is the part that matters most to you?"],
            2: [f"Interesting{name}. Keep going.", f"I'm following{name}. What happened next?", f"All right{name}, you have my attention. Give me the next piece."],
            3: [f"You have my attention{name}. Continue."],
        }

    return choose_response(options, level, previous_response)
