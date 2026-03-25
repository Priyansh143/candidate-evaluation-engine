import faiss
import numpy as np
# from backend.resume_extractor import preprocess_resume
from backend.embeddings import EmbeddingModel
from backend.profile_loader import load_profile, profile_to_chunks 
from backend.logger import setup_run_logger
from backend.resume_extractor import preprocess_resume

class ResumeFAISS:
    """
    Builds a FAISS index over resume chunks once
    and allows semantic search over them.
    """

    def __init__(self, resume_pdf: str=None, logger=None):
        if logger is None:
            class DummyLogger:
                def info(self, *args, **kwargs): pass
            logger = DummyLogger()
        # 1. Extract & preprocess resume
        logger.info("\nRESUME PREPROCESSING STARTED\n")
        logger.info(f"Preprocessing resume: {resume_pdf}")
        
        if(not resume_pdf):
            profile_path = "data/profile.json"
            profile = load_profile(profile_path)   # now passing JSON path
            chunks = profile_to_chunks(profile)
            if not chunks:
                raise ValueError("No resume chunks found to index.")

            # 2. Load embedding model
            self.embedder = EmbeddingModel()
            
            # 🔹 embed only the text
            texts = [
                f"{c['section']} | {c['context']} | {c['text']}"
                for c in chunks
            ]
            embeddings = self.embedder.encode(texts)
            logger.info(f"Generated embeddings for {len(texts)} resume chunks.")

            # 4. Normalize embeddings for cosine similarity
            # faiss.normalize_L2(embeddings) already done in embedder.encode()

            # 5. Build FAISS index (Inner Product = cosine after normalization)
            dim = embeddings.shape[1]
            self.index = faiss.IndexFlatIP(dim)
            self.index.add(embeddings)

            # 6. Store raw text
            self.text_store = chunks
            logger.info("FAISS index built successfully.\n")
            return
        else:
            chunks = preprocess_resume(pdf_path = resume_pdf, logger=logger)
            if not chunks:
                raise ValueError("No resume chunks found to index.")

            # 2. Load embedding model
            self.embedder = EmbeddingModel()
            
            # 🔹 embed only the text
            texts = [c['text'] for c in chunks]
            embeddings = self.embedder.encode(texts)
            logger.info(f"Generated embeddings for {len(texts)} resume chunks.")

            # 4. Normalize embeddings for cosine similarity
            # faiss.normalize_L2(embeddings) already done in embedder.encode()

            # 5. Build FAISS index (Inner Product = cosine after normalization)
            dim = embeddings.shape[1]
            self.index = faiss.IndexFlatIP(dim)
            self.index.add(embeddings)

            # 6. Store raw text
            self.text_store = chunks
            logger.info("FAISS index built successfully.\n")


    def search(self, topic_objects: list[dict], top_k: int = 5, threshold: float = 0.55, resume_path: str = None, logger=None) -> list[list[str]]:
        """
        Search resume for evidence relevant to each topic.
        Returns list aligned with topic order.
        Each element contains one formatted evidence string.
        """
        if logger is None:
            class DummyLogger:
                def info(self, *args, **kwargs): pass
            logger = DummyLogger()
        logger.info("\nRESUME SEARCH STARTED INSIDE SEARCH FUNCTION\n")
        if not topic_objects:
            return []
        
        if resume_path:

            # Build semantic queries from topic + keywords
            queries = [
                topic["topic"] + " " + " ".join(topic.get("keywords", []))
                for topic in topic_objects
            ]

            query_with_prefix = [
                f"search for relevant passages using the keywords: {q}"
                for q in queries
            ]
            logger.info("Generated semantic queries.")
            logger.info(f"Queries:\n{query_with_prefix}")
            # Embed queries
            query_emb = self.embedder.encode(query_with_prefix)
            faiss.normalize_L2(query_emb)

            # FAISS search
            scores, indices = self.index.search(query_emb, top_k)

            results = []

            for q_scores, q_indices in zip(scores, indices):

                # group evidence by section
                section_groups = {
                    "PROJECTS": {},
                    "EXPERIENCE": {},
                    "RESEARCH": {}
                }

                for score, idx in zip(q_scores, q_indices):

                    if idx == -1:
                        continue

                    if score < threshold:
                        continue

                    chunk = self.text_store[idx]

                    text = chunk["text"]
                    section = chunk["section"]
                    context = chunk.get("context")

                    # remove weak / short lines
                    # if len(text.split()) < 6:
                    #     continue

                    if section in section_groups:
                        
                        if context not in section_groups[section]:
                            section_groups[section][context] = []
                            
                        section_groups[section][context].append(text)

                # append evidence per section
                evidence_parts = []

                if section_groups["EXPERIENCE"]:

                    section_text = ["Professional Experience:"]
                    counter = 1

                    for context, sentences in section_groups["EXPERIENCE"].items():

                        section_text.append(f"{counter}. {context}")
                        for s in sentences:
                            section_text.append(f"- {s}")

                        counter += 1

                    evidence_parts.append("\n".join(section_text))


                if section_groups["PROJECTS"]:

                    section_text = ["Project Experience:"]
                    counter = 1

                    for context, sentences in section_groups["PROJECTS"].items():

                        section_text.append(f"{counter}. {context}")
                        for s in sentences:
                            section_text.append(f"- {s}")

                        counter += 1

                    evidence_parts.append("\n".join(section_text))

                if section_groups["RESEARCH"]:
                    
                    section_text = ["Research Experience:"]
                    counter = 1

                    for context, sentences in section_groups["RESEARCH"].items():

                        section_text.append(f"{counter}. {context}")
                        for s in sentences:
                            section_text.append(f"- {s}")

                        counter += 1
                    evidence_parts.append("\n".join(section_text))

                evidence_string = "\n\n".join(evidence_parts)

                # store aligned with query index
                results.append([evidence_string])

            return results
        
        #If profile exists, use profile-based evidence retrieval)
        # Build semantic queries from topic + keywords
        queries = [
            topic["topic"] + " " + " ".join(topic.get("keywords", []))
            for topic in topic_objects
        ]

        query_with_prefix = [
            f"search for relevant passages using the keywords: {q}"
            for q in queries
        ]
        logger.info("Generated semantic queries.")
        logger.info(f"Queries:\n{query_with_prefix}")
        # Embed queries
        query_emb = self.embedder.encode(query_with_prefix)
        faiss.normalize_L2(query_emb)

        # FAISS search
        scores, indices = self.index.search(query_emb, top_k)
        logger.info(f"scores: {scores}\n indices: {indices}")

        results = []

        for q_scores, q_indices in zip(scores, indices):

            # group evidence by section
            section_groups = {
                "PROJECTS": {},
                "EXPERIENCE": {},
                "RESEARCH": {},
                "SKILLS": [],
                "ACHIEVEMENTS": []
            }

            for score, idx in zip(q_scores, q_indices):

                if idx == -1:
                    continue

                if score < threshold:
                    continue

                chunk = self.text_store[idx]

                text = chunk["text"]
                section = chunk["section"]
                context = chunk.get("context")
                context = context or "General"

                # remove weak / short lines
                # if len(text.split()) < 6:
                #     continue
                if section == "SKILLS":
                  section_groups["SKILLS"].append(text)
                  continue
                
                if section == "ACHIEVEMENTS":
                    section_groups["ACHIEVEMENTS"].append(text)
                    continue
                  
                if section in section_groups:
                    
                    if context not in section_groups[section]:
                        section_groups[section][context] = []
                        
                    section_groups[section][context].append(text)

            # append evidence per section
            evidence_parts = []

            if section_groups["EXPERIENCE"]:

                section_text = ["Professional Experience:"]
                counter = 1

                for context, sentences in section_groups["EXPERIENCE"].items():

                    section_text.append(f"{counter}. {context}")
                    for s in sentences:
                        section_text.append(f"- {s}")

                    counter += 1

                evidence_parts.append("\n".join(section_text))


            if section_groups["PROJECTS"]:

                section_text = ["Project Experience:"]
                counter = 1

                for context, sentences in section_groups["PROJECTS"].items():

                    section_text.append(f"{counter}. {context}")
                    for s in sentences:
                        section_text.append(f"- {s}")

                    counter += 1

                evidence_parts.append("\n".join(section_text))

            if section_groups["RESEARCH"]:
                
                section_text = ["Research Experience:"]
                counter = 1

                for context, sentences in section_groups["RESEARCH"].items():

                    section_text.append(f"{counter}. {context}")
                    for s in sentences:
                        section_text.append(f"- {s}")

                    counter += 1
                evidence_parts.append("\n".join(section_text))
                
            if section_groups["SKILLS"]:
                evidence_parts.append(
                    "Skills:\n" + "\n".join(f"- {s}" for s in section_groups["SKILLS"])
                )
            
            if section_groups["ACHIEVEMENTS"]:
                evidence_parts.append(
                    "Achievements:\n" + "\n".join(f"- {a}" for a in section_groups["ACHIEVEMENTS"])
                )

            if not evidence_parts:
                results.append(["No strong evidence found."])
                continue
            evidence_string = "\n\n".join(evidence_parts)

            # store aligned with query index
            results.append([evidence_string])

        return results

# local test 
if __name__ == "__main__":
    logger = setup_run_logger()
    print("Building FAISS index...")
    faiss_service = ResumeFAISS("profile.json", logger)
    print("Index ready.\n")
    jd_priorities = [
        {
        "topic": "model deployment",
        "keywords": ["deployed","model serving","fastapi","docker","production pipeline"]
        },
        {
        "topic": "feature engineering",
        "keywords": ["feature engineering","feature selection","feature extraction","data preprocessing","feature transformation"]
        }
        ]
    evidence = faiss_service.search(jd_priorities, top_k=3, threshold=0.5, logger = logger)
    for priority, ev in zip(jd_priorities, evidence):
        print(f"JD Priority: {priority}")
        if ev:
            for i, e in enumerate(ev, 1):
                print(f"{e}")
        else:
            print("  No strong evidence found.")
        print()