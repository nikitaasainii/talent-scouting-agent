import os
import sys
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
from chromadb.utils import embedding_functions
from schemas.candidate_schema import Candidate

def seed_from_candidates(candidates: list[Candidate]):
    if not candidates:
        print("⚠ No candidates to seed.")
        return
    print(f"Seeding {len(candidates)} candidates into ChromaDB...")

    db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
    client = chromadb.PersistentClient(path=db_path)

    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    # Reset collection on each run
    try:
        client.delete_collection("candidates")
    except:
        pass

    collection = client.create_collection(
        name="candidates",
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}
    )

    documents, metadatas, ids = [], [], []

    for c in candidates:
        # Rich document for semantic search
        doc = f"""
        Name: {c.name}
        Role: {c.current_role}
        Skills: {', '.join(c.skills)}
        Location: {c.location}
        Experience: {c.total_experience_years} years
        Bio: {c.bio}
        Top Repos: {', '.join(c.top_repositories)}
        Summary: {c.enriched_summary}
        """.strip()

        documents.append(doc)
        metadatas.append({
            "candidate_id": c.id,
            "name": c.name,
            "github_url": c.github_url,
            "skills": ", ".join(c.skills),
            "experience_years": c.total_experience_years,
            "location": c.location
        })
        ids.append(c.id)

    collection.add(documents=documents, metadatas=metadatas, ids=ids)

    # Save candidates to JSON as backup
    output_path = os.path.join(os.path.dirname(__file__), "candidates.json")
    with open(output_path, "w") as f:
        json.dump([c.model_dump() for c in candidates], f, indent=2)

    print(f"✅ ChromaDB seeded — {collection.count()} vectors")
    print(f"✅ candidates.json saved as backup")