# RAG Policy Assistant Design

The **RAG (Retrieval-Augmented Generation) Policy Assistant** is a context-aware chat copilot integrated into the claim detail page. It enables claims adjusters and members to query insurance policy terms in natural language.

---

## 1. Complete System Isolation

The Policy Assistant is strictly isolated from the core claim adjudication pipeline:
- The chatbot has **read-only access** to the claims database and policy documents.
- It **never participates** in claim approvals, rejections, co-pay calculations, or override logic.
- This design ensures security and prevents LLM model hallucinations from affecting final financial decisions.

---

## 2. RAG Knowledge Base & Chunking

The assistant indexes two primary text documents representing the policy guidelines:
1. `policy_terms.json`: Structured definitions of coverage dates, member lists, and disease waiting periods.
2. `adjudication_rules.md`: Business guidelines, exclusions, co-pay percentages, and diagnostic scan sub-limits.

### Indexing Pipeline:
- **Chunking**: Text documents are chunked into paragraphs (~200 tokens each) with a overlap of 50 tokens to maintain context continuity.
- **Embedding Generation**: Text chunks are passed to the Gemini Embedding API to generate vectors.
- **Vector Vector Database**: Vectors are stored in PostgreSQL using the `pgvector` extension (or a local NumPy vector fallback if the database connection is absent).

---

## 3. Retrieval & Generative Synthesis

When an adjuster asks a question:
1. The user's query is converted to a vector embedding.
2. A cosine similarity search queries the top-3 nearest text chunks.
3. The query and retrieved policy text are compiled into a prompt template:

```text
You are the Plum OPD Policy Copilot. Answer the query based ONLY on the policy terms below.
Cite the relevant source sections.

Context:
---
[Source: adjudication_rules.md]
{retrieved_chunk_1}
---
[Source: policy_terms.json]
{retrieved_chunk_2}

Query: {user_query}
Answer:
```

4. Gemini synthesizes a grounded answer, which the UI displays along with clickable source citations.
