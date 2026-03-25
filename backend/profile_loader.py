import json
from backend.models import Profile


def load_profile(path: str) -> Profile:
    with open(path, "r") as f:
        data = json.load(f)

    return Profile(**data)


def profile_to_chunks(profile: Profile):
    chunks = []

    for exp in profile.experience:
        context = " - ".join(filter(None, [exp.company, exp.role]))

        for point in exp.points:
            chunks.append({
                "text": point,
                "section": "EXPERIENCE",
                "context": context
            })

    for proj in profile.projects:
        context = proj.name

        for point in proj.points:
            chunks.append({
                "text": point,
                "section": "PROJECTS",
                "context": context
            })
            
    for res in profile.research:
        context = res.name

        for point in res.points:
            chunks.append({
                "text": point,
                "section": "RESEARCH",
                "context": context
            })
            
    for skill in profile.skills:
        if not skill.strip():
            continue
        chunks.append({
            "text": skill,
            "section": "SKILLS",
            "context": None
        })
        
    for ach in profile.achievements:
        chunks.append({
            "text": ach,
            "section": "ACHIEVEMENTS",
            "context": None
        })

    return chunks