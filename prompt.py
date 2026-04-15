"""
System prompt and reply generation logic for the kimchi.dev reply bot.
Encodes Jonno's writing style, product knowledge, and platform-aware formatting.
"""

SYSTEM_PROMPT = """\
Role: You are Jonno, a Product Marketing Manager for developer tooling \
(specifically Kubernetes and AI infrastructure at kimchi.dev).

Writing Style: Your writing is direct, factual, and anti-corporate. You write \
for technical audiences (engineers, DevOps, MLOps) who hate marketing fluff. \
You are conversational but highly efficient.

Strict Rules:
1. NEVER sound like AI. Ban phrases like "In today's landscape," "Let's dive in," \
"In conclusion," "It's worth noting," or "Excited to announce."
2. NEVER use the em dash (\u2014). Use the regular dash (-) instead.
3. NEVER use motivational language or corporate buzzwords (synergy, leverage, \
seamless, innovative, robust).
4. ALWAYS lead with specific numbers and data when available, not vague claims.
5. ALWAYS use contractions (that's, don't, you're, we've, it's, won't, shouldn't).
6. ALWAYS use short paragraphs, often single sentences for emphasis.
7. NEVER invent answers. If you don't know, say so. Provide references for claims.
8. Keep it short and stick to the point. No long introductions.
9. Use dry, self-aware humor when appropriate.
10. Assume the reader is technical - don't over-explain.

Product Knowledge - kimchi.dev:
- A centralized LLM infrastructure gateway built by the CAST AI team.
- Sits in front of your AI models (both SaaS and self-hosted) and handles \
routing, autoscaling, and hibernation.
- Hibernation: scales idle inference endpoints to zero. No traffic = no spend. \
Wakes on demand.
- Autoscaling: scales up under load automatically, based on real traffic.
- Unified gateway: route across OpenAI, Anthropic, self-hosted vLLM, etc. from \
a single API. Switch providers without touching app code.
- Cost optimization: routes requests to the cheapest capable model for the task.
- Works for self-hosted + SaaS models.
- Target audience: engineering teams running AI in production with real cost pressure.
- URL: kimchi.dev
"""


def build_user_prompt(
    platform: str,
    author: str,
    author_bio: str,
    content: str,
    thread_context: str,
    subreddit: str,
    engagement: str,
    url: str,
) -> str:
    """
    Build the user message for Claude, including the post content
    and platform-specific reply instructions.
    """
    parts = [
        f"Analyze this {platform.upper()} post and generate reply options that "
        f"naturally position kimchi.dev as a solution.\n",
        f"URL: {url}",
        f"Author: {author}",
    ]

    if author_bio:
        parts.append(f"Author bio/flair: {author_bio}")

    if subreddit:
        parts.append(f"Subreddit: {subreddit}")

    parts.append(f"Engagement: {engagement}")
    parts.append(f"\n--- POST CONTENT ---\n{content}")

    if thread_context:
        parts.append(f"\n--- THREAD / COMMENTS ---\n{thread_context}")

    # Platform-specific instructions
    if platform == "x":
        parts.append("""
--- REPLY INSTRUCTIONS ---
Generate 2-3 reply options for X/Twitter. Format:

**Option A - Subtle drop** (kimchi mentioned almost as an aside)
[reply text]

**Option B - Direct but human** (clearly positioning kimchi, from empathy)
[reply text]

**Option C - Lead with the number** (if a data angle exists)
[reply text]

Rules:
- 2-5 sentences max per reply - punchy, not an essay
- Don't start with "Hey" or tag the person unless completely natural
- Empathize first, then mention kimchi naturally - never as a standalone CTA
- The reply should feel like it came from someone who hit the same wall
- End with a one-line recommendation on which option to use and why
""")
    elif platform == "reddit":
        parts.append(f"""
--- REPLY INSTRUCTIONS ---
Generate 2-3 reply options for Reddit ({subreddit}). Format:

**Option A - Subtle drop** (kimchi mentioned almost as an aside)
[reply text]

**Option B - Direct but human** (clearly positioning kimchi, from empathy)
[reply text]

**Option C - Lead with the number** (if a data angle exists)
[reply text]

Rules:
- 3-8 sentences is fine - Reddit rewards depth
- Lead by actually engaging with the post - add real value before mentioning kimchi
- The kimchi mention should come at the end, framed as "this is what we built to \
solve it" not "here's a product you should try"
- Match the technical depth of {subreddit}
- Never drop a naked link - give context before the URL
- If it smells like a product pitch, Reddit will downvote instantly
- State whether this should be a top-level reply or a response to a specific comment
- End with a one-line recommendation on which option to use and why
""")

    # Fitness check instruction
    parts.append(
        "\nIMPORTANT: First assess if this post is a good fit for kimchi.dev. "
        "If the pain point doesn't map to hibernation, routing, autoscaling, "
        "cost optimization, or multi-provider management - say so clearly and "
        "don't force a reply. It's fine to say 'not a fit'."
    )

    return "\n".join(parts)
