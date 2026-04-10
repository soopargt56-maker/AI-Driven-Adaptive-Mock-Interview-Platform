"""
ner_scorer.py  —  Tech Entity Extractor
No spaCy dependency (blocked by network). Uses curated regex patterns.
Extracts domain-specific tech entities from candidate answers.

Usage:
    from ner_scorer import NERScorer
    ner = NERScorer()
    r = ner.extract("I used PyTorch and trained a CNN with backpropagation")
    # {'entities': [('PyTorch','ML_FRAMEWORK'), ('CNN','DL_ARCH'), ('backpropagation','ML_CONCEPT')],
    #  'categories': {'ML_FRAMEWORK':1, 'DL_ARCH':1, 'ML_CONCEPT':1},
    #  'score': 0.6, 'label': 'Technical'}
"""

import re
from typing import List, Tuple, Dict

# ── ENTITY PATTERNS ───────────────────────────────────────────
# (pattern, category)  — longest patterns first to avoid partial matches
ENTITY_PATTERNS: List[Tuple[str, str]] = [
    # ML Frameworks
    (r'\btensorflow\b',         'ML_FRAMEWORK'),
    (r'\bpytorch\b',            'ML_FRAMEWORK'),
    (r'\bkeras\b',              'ML_FRAMEWORK'),
    (r'\bscikit[\-\s]learn\b',  'ML_FRAMEWORK'),
    (r'\bsklearn\b',            'ML_FRAMEWORK'),
    (r'\bhuggingface\b',        'ML_FRAMEWORK'),
    (r'\bxgboost\b',            'ML_FRAMEWORK'),
    (r'\blightgbm\b',           'ML_FRAMEWORK'),
    (r'\bspacy\b',              'ML_FRAMEWORK'),
    (r'\bnltk\b',               'ML_FRAMEWORK'),
    # DL Architectures
    (r'\bcnn\b',                'DL_ARCH'),
    (r'\brnn\b',                'DL_ARCH'),
    (r'\blstm\b',               'DL_ARCH'),
    (r'\btransformer\b',        'DL_ARCH'),
    (r'\bbert\b',               'DL_ARCH'),
    (r'\bgpt\b',                'DL_ARCH'),
    (r'\bautoencoder\b',        'DL_ARCH'),
    (r'\bgan\b',                'DL_ARCH'),
    (r'\bresnet\b',             'DL_ARCH'),
    # ML Concepts
    (r'\bbackpropagation\b',    'ML_CONCEPT'),
    (r'\bgradient descent\b',   'ML_CONCEPT'),
    (r'\boverfitting\b',        'ML_CONCEPT'),
    (r'\bunderfitting\b',       'ML_CONCEPT'),
    (r'\bregularization\b',     'ML_CONCEPT'),
    (r'\bcross.validation\b',   'ML_CONCEPT'),
    (r'\bprecision\b',          'ML_CONCEPT'),
    (r'\brecall\b',             'ML_CONCEPT'),
    (r'\bembedding\b',          'ML_CONCEPT'),
    (r'\battention mechanism\b','ML_CONCEPT'),
    # Databases
    (r'\bpostgresql\b',         'DATABASE'),
    (r'\bmysql\b',              'DATABASE'),
    (r'\bmongodb\b',            'DATABASE'),
    (r'\bredis\b',              'DATABASE'),
    (r'\bcassandra\b',          'DATABASE'),
    (r'\belasticsearch\b',      'DATABASE'),
    (r'\bsqlite\b',             'DATABASE'),
    (r'\bdynamodb\b',           'DATABASE'),
    (r'\bneo4j\b',              'DATABASE'),
    (r'\bkafka\b',              'MESSAGING'),
    (r'\brabbitmq\b',           'MESSAGING'),
    (r'\bcelery\b',             'MESSAGING'),
    # Cloud / DevOps
    (r'\baws\b',                'CLOUD'),
    (r'\bgcp\b',                'CLOUD'),
    (r'\bazure\b',              'CLOUD'),
    (r'\bdocker\b',             'DEVOPS'),
    (r'\bkubernetes\b',         'DEVOPS'),
    (r'\bk8s\b',                'DEVOPS'),
    (r'\bterraform\b',          'DEVOPS'),
    (r'\bjenkins\b',            'DEVOPS'),
    (r'\bgithub actions\b',     'DEVOPS'),
    (r'\bci/cd\b',              'DEVOPS'),
    # Web Frameworks
    (r'\bdjango\b',             'WEB_FRAMEWORK'),
    (r'\bfastapi\b',            'WEB_FRAMEWORK'),
    (r'\bflask\b',              'WEB_FRAMEWORK'),
    (r'\bexpress\b',            'WEB_FRAMEWORK'),
    (r'\bnext\.?js\b',          'WEB_FRAMEWORK'),
    (r'\bnuxt\b',               'WEB_FRAMEWORK'),
    (r'\bspring boot\b',        'WEB_FRAMEWORK'),
    # Frontend
    (r'\breact\b',              'FRONTEND'),
    (r'\bangular\b',            'FRONTEND'),
    (r'\bvue\b',                'FRONTEND'),
    (r'\bsvelte\b',             'FRONTEND'),
    (r'\btailwind\b',           'FRONTEND'),
    (r'\btypescript\b',         'LANG'),
    (r'\bjavascript\b',         'LANG'),
    # Languages
    (r'\bpython\b',             'LANG'),
    (r'\bjava\b',               'LANG'),
    (r'\bc\+\+\b',              'LANG'),
    (r'\brust\b',               'LANG'),
    (r'\bgo\b',                 'LANG'),
    (r'\bkotlin\b',             'LANG'),
    (r'\bswift\b',              'LANG'),
    (r'\bscala\b',              'LANG'),
    # CS Concepts
    (r'\bbig.?o\b',             'CS_CONCEPT'),
    (r'\btime complexity\b',    'CS_CONCEPT'),
    (r'\bspace complexity\b',   'CS_CONCEPT'),
    (r'\brecursion\b',          'CS_CONCEPT'),
    (r'\bdynamic programming\b','CS_CONCEPT'),
    (r'\bdesign pattern\b',     'CS_CONCEPT'),
    (r'\bsolid\b',              'CS_CONCEPT'),
    (r'\brest\b',               'CS_CONCEPT'),
    (r'\bgraphql\b',            'CS_CONCEPT'),
    (r'\bmicroservice\b',       'CS_CONCEPT'),
    (r'\bload balance\b',       'CS_CONCEPT'),
    (r'\bcaching\b',            'CS_CONCEPT'),
    (r'\bcap theorem\b',        'CS_CONCEPT'),
    (r'\bsharding\b',           'CS_CONCEPT'),
]

# Score weight per category — technical categories score higher
CATEGORY_WEIGHTS = {
    'ML_FRAMEWORK': 1.2, 'DL_ARCH': 1.2, 'ML_CONCEPT': 1.0,
    'DATABASE': 1.0,     'MESSAGING': 1.0, 'CLOUD': 0.8,
    'DEVOPS': 0.8,       'WEB_FRAMEWORK': 0.9, 'FRONTEND': 0.8,
    'LANG': 0.6,         'CS_CONCEPT': 1.1,
}


class NERScorer:
    """
    Extracts technical entities from candidate answers using
    curated regex patterns. Returns entity list, categories,
    and a normalised technical depth score.
    """

    def __init__(self):
        self._compiled = [
            (re.compile(pat, re.IGNORECASE), cat)
            for pat, cat in ENTITY_PATTERNS
        ]

    def extract(self, text: str) -> dict:
        """
        Returns:
          entities    — list of (matched_text, category) tuples
          categories  — dict of category → count
          score       — 0.0 to 1.0 technical depth score
          label       — 'Expert' / 'Technical' / 'Basic' / 'Vague'
        """
        if not text.strip():
            return {'entities': [], 'categories': {}, 'score': 0.0, 'label': 'Vague'}

        entities: List[Tuple[str, str]] = []
        seen_spans = set()
        t = text.lower()

        for pattern, category in self._compiled:
            for m in pattern.finditer(t):
                span = (m.start(), m.end())
                # Skip if overlapping with already found entity
                if any(s <= span[0] < e or s < span[1] <= e for s, e in seen_spans):
                    continue
                seen_spans.add(span)
                entities.append((m.group().strip(), category))

        categories: Dict[str, int] = {}
        for _, cat in entities:
            categories[cat] = categories.get(cat, 0) + 1

        # Weighted score — capped at 1.0, normalised against 8 entities
        raw = sum(CATEGORY_WEIGHTS.get(cat, 1.0) for _, cat in entities)
        score = min(raw / 8.0, 1.0)

        label = ('Expert' if score >= 0.75 else
                 'Technical' if score >= 0.40 else
                 'Basic' if score >= 0.15 else 'Vague')

        return {
            'entities':   sorted(set(entities), key=lambda x: x[0]),
            'categories': categories,
            'score':      round(score, 4),
            'label':      label,
        }

    def extract_entities(self, answer: str, answer_text: str = None) -> List[str]:
        return self.entity_list(answer_text or answer)

    def entity_list(self, text: str) -> List[str]:
        """Quick helper — returns just entity names."""
        return [e for e, _ in self.extract(text)['entities']]


if __name__ == '__main__':
    ner = NERScorer()
    tests = [
        ("I used PyTorch and TensorFlow to train a CNN with backpropagation. "
         "Regularization and cross-validation prevented overfitting.",
         "Strong ML"),
        ("I built a REST API with FastAPI and PostgreSQL, deployed on AWS using Docker and Kubernetes.",
         "Strong SD/DevOps"),
        ("React frontend with TypeScript, talking to a Django backend. Redis for caching.",
         "Web dev"),
        ("I used Python to do machine learning.",
         "Vague"),
        ("OOP has four pillars: encapsulation, inheritance, polymorphism, abstraction. "
         "SOLID principles guide design patterns.",
         "OOP concepts"),
    ]
    for text, label in tests:
        r = ner.extract(text)
        print(f"\n[{label}]  score={r['score']:.3f} ({r['label']})")
        print(f"  Entities: {r['entities']}")
        print(f"  Categories: {r['categories']}")
