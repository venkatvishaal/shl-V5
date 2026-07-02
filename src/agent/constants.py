"""Shared constants for the agent layer."""

_SKILL_KEYWORDS = [
    # Technical skills
    "java", "python", "javascript", "typescript", "react", "node", "sql",
    "spring", "django", "flask", "kubernetes", "docker", "aws", "azure",
    "machine learning", "data science", "analytics", "excel", "powerbi",
    "salesforce", "sap", "c++", ".net", "ruby", "go", "rust",
    "cloud", "devops", "ci/cd", "terraform", "linux",
    # Soft skills
    "project management", "agile", "scrum",
    "leadership", "communication", "teamwork", "negotiation", "sales",
    "customer service", "stakeholder management", "problem solving",
    "critical thinking", "decision making", "conflict resolution",
    "emotional intelligence", "adaptability", "time management",
    # Domain specific skills (added V3)
    "accounting", "hr", "marketing", "ux", "operations", "compliance",
    # Assessment-specific (keep generic cognitive indicators, but strip OPQ/personality from skill counts)
    "numerical", "verbal", "logical reasoning",
    "situational judgment", "cognitive ability",
    "mechanical reasoning", "error checking", "reading comprehension",
]
