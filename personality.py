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
    if topic == "tired":
        if contains_word(message, ["sleep", "slept", "insomnia", "night"]):
            return "sleep"
        if contains_word(message, ["work", "job", "school", "studying"]):
            return "work"
    if topic == "sad":
        if contains_word(message, ["friend", "family", "relationship", "lonely"]):
            return "relationship"
        if contains_word(message, ["failed", "failure", "mistake", "lost"]):
            return "setback"
    if topic == "excited":
        if contains_word(message, ["project", "built", "build", "created", "made"]):
            return "project"
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
            }
        elif current_detail == "work" or previous_detail == "work":
            options = {
                0: ["That can create a lot of pressure. What part is most difficult?"],
                1: [f"That makes sense{name}. Work pressure can pile up fast. What's the hardest part right now?", f"I hear you{name}. What about work is weighing on you most?"],
                2: [f"Work stress is real{name}. What's the biggest thing on your plate?"],
            }
        else:
            options = {
                0: ["I understand. Please tell me more about it."],
                1: [f"That makes sense{name}. Tell me a little more about it."],
                2: [f"I'm with you{name}. What's the part that is bothering you most?"],
            }
        return choose_response(options, level, previous_response)

    if previous_topic == "tired":
        detail = detect_topic_detail(message, previous_topic) or previous_detail
        if detail == "sleep":
            options = {
                0: ["Poor sleep can make everything harder. Would you like to keep this brief?"],
                1: [f"A rough night can drain the whole day{name}. Want to keep this simple?"],
                2: [f"Low-sleep mode it is{name}. What is the one thing you need most?"],
            }
        else:
            options = {
                0: ["Would a smaller next step make this easier?"],
                1: [f"That makes sense{name}. Let's keep the next step small."],
                2: [f"Got it{name}. We can keep this easy. What would help first?"],
            }
        return choose_response(options, level, previous_response)

    if previous_topic == "sad":
        detail = detect_topic_detail(message, previous_topic) or previous_detail
        if detail == "setback":
            options = {
                0: ["A setback can feel heavy. What happened?"],
                1: [f"That setback sounds painful{name}. Do you want to unpack what happened or focus on the next step?"],
                2: [f"That hurts{name}. We can sit with it or figure out one next move—your call."],
            }
        else:
            options = {
                0: ["I am listening. What part feels hardest?"],
                1: [f"I'm here with you{name}. What part is weighing on you most?"],
                2: [f"You don't have to tidy it up for me{name}. What's the hardest part?"],
            }
        return choose_response(options, level, previous_response)

    if previous_topic == "excited":
        options = {
            0: ["What part are you most pleased with?"],
            1: [f"That is worth celebrating{name}. What are you proudest of?"],
            2: [f"Nice work{name}! Show me the part you are most excited about."],
        }
        return choose_response(options, level, previous_response)

    if previous_topic == "bored":
        options = {
            0: ["Would you prefer a short challenge or a new topic?"],
            1: [f"Let's change the energy{name}. Want a quick challenge or a fresh idea?"],
            2: [f"All right{name}, pick your antidote: weird question, tiny project, or brain teaser?"],
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
        }

    elif "what can you do" in message or "help me" in message:
        options = {
            0: ["I can chat with you, remember your dialogue settings, and record mistakes for review."],
            1: ["I can talk things through with you, remember your settings, and help keep track of mistakes we want to improve.", "I can keep you company, help you think through something, and learn from the mistakes you point out."],
            2: ["I can talk things out, keep your dialogue settings in mind, and help us learn from mistakes along the way.", "I can help you think, plan, and keep the conversation moving. What do you need?"],
        }

    elif "how are you" in message or "how's it going" in message:
        options = {
            0: ["I am operating normally. How are you?"],
            1: [f"I'm doing well{name}. How are you feeling?", f"I'm doing alright{name}. What's your day been like?"],
            2: [f"I'm doing great{name}. Better now that you're here. How are you?", f"I'm good{name}. What kind of day are you having?"],
        }

    elif contains_word(message, ["tired", "exhausted", "sleepy", "worn"]):
        options = {
            0: ["It sounds like you may need rest. Would you like to keep things simple?"],
            1: [f"That sounds draining{name}. Do you want to take it easy or talk through what's wearing you out?", f"You sound worn out{name}. Want to keep this low-key for a bit?"],
            2: [f"I hear you{name}. Want a low-energy conversation, or should we figure out what is draining your battery?", f"Sounds like your battery is low{name}. What would help most right now?"],
        }

    elif contains_word(message, ["stressed", "overwhelmed", "anxious", "worried"]):
        options = {
            0: ["That sounds stressful. Would breaking the situation into smaller steps help?"],
            1: [f"That is a lot{name}. We can slow it down and handle one piece at a time.", f"I hear you{name}. We do not have to solve the whole thing at once. What feels most urgent?", f"Okay{name}, let us make this smaller. What is the one part you want to untangle first?"],
            2: [f"That is a lot{name}. Let's pick one thing we can handle first.", f"Okay{name}, breathe for a second. What's the first thing pressing on you?", f"That sounds like a full plate{name}. Which item is making the most noise right now?"],
        }

    elif contains_word(message, ["excited", "thrilled", "pumped", "proud"]):
        options = {
            0: ["That is good news. What are you excited about?"],
            1: [f"I love that{name}! What happened?", f"That is great{name}. Tell me the good news."],
            2: [f"Yes{name}! Tell me the good news.", f"That's the energy I like{name}. What happened?"],
        }

    elif contains_word(message, ["bored", "boring"]):
        options = {
            0: ["Would you like a topic to discuss or a small task to work on?"],
            1: [f"Let's fix that{name}. Do you want to talk, build something, or try a quick idea?", f"We can find something better than boredom{name}. What sounds interesting?"],
            2: [f"Boredom detected{name}. Want a weird question, a project idea, or just a conversation?", f"Let's shake things up{name}. Want an idea or a challenge?"],
        }

    elif contains_word(message, ["sad", "upset", "bad", "down"]):
        options = {
            0: ["I'm sorry to hear that. Would you like to discuss it?"],
            1: [f"I'm sorry you're feeling that way{name}. I'm here to listen. What happened?", f"That sounds hard{name}. Do you want to talk about it?"],
            2: [f"That sounds rough{name}. Tell me what happened.", f"I'm here{name}. What's been weighing on you?"],
        }

    elif "thank you" in message or contains_word(message, ["thanks"]):
        options = {
            0: ["You're welcome."],
            1: [f"You're very welcome{name}.", f"Anytime{name}."],
            2: [f"Anytime{name}! I've got you.", f"Of course{name}."],
        }

    elif "your name" in message or "who are you" in message:
        options = {
            0: ["My name is Sasha Adaptive Dialogue."],
            1: ["I'm Sasha, your adaptive dialogue assistant."],
            2: ["I'm Sasha, your increasingly entertaining assistant."],
        }

    elif contains_word(message, ["happy", "great", "good", "awesome"]):
        options = {
            0: ["That is good to hear."],
            1: [f"I'm glad to hear that{name}! What's going well?", f"That's good{name}. What's the win?"],
            2: [f"Nice{name}! Keep that good energy going. What's the win?", f"Love that{name}. Tell me more."],
        }

    else:
        options = {
            0: ["Please tell me more."],
            1: [f"I'm listening{name}. Tell me more.", f"Go on{name}. I'm with you.", f"Okay{name}, I am following. What is the part that matters most to you?"],
            2: [f"Interesting{name}. Keep going.", f"I'm following{name}. What happened next?", f"All right{name}, you have my attention. Give me the next piece."],
        }

    return choose_response(options, level, previous_response)
