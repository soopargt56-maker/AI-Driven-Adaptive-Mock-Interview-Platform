def generate_feedback(answer=None, answer_text=None, question=None, ideal_answer=None, skill=None, sub_domain=None, nlp_score=None, svm_label=None, kg_score=None, final_score=None, ner_entities=None):
    text = answer_text or answer or ""
    word_count = len(text.split())
    
    content = []
    strengths = []
    next_step = ""

    # Rule 1: Length evaluation
    if word_count < 20:
        content.append("Your response was very brief. Technical answers usually require more elaboration.")
        next_step = "Try expanding on the 'why' and 'how' behind your answer."
    elif word_count > 150:
        content.append("You provided a highly detailed explanation.")
        strengths.append("Comprehensive")
        next_step = "Ensure you don't lose the main point in the details. Keep it concise."
    else:
        content.append("Good length and pacing.")
        strengths.append("Concise")
        
    # Rule 2: Keyword Evaluation
    if ner_entities and len(ner_entities) > 2:
        content.append(f"You successfully included key technical entities like: {', '.join(ner_entities[:3])}.")
        strengths.append("Technical Vocabulary")
    elif ner_entities:
        content.append("You mentioned some core concepts, but there is room for deeper technical vocabulary.")
    else:
        content.append("Your answer lacked specific technical keywords associated with this topic.")
        next_step = "Try incorporating precise industry terminology."

    # Rule 3: Overall Performance
    if svm_label == "Good":
        strengths.append("High Relevance")
        if not next_step:
            next_step = "Maintain this level of detail for future questions."
    elif svm_label == "Poor":
        next_step = "Review the core concepts for this topic before the real interview."

    if not next_step:
        next_step = "Continue to the next round."

    return {
        "content": content,
        "strengths": strengths,
        "next_step": next_step
    }
