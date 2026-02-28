"""Brave Search and web fetch tools for documentation and research."""

import httpx


UNITY_DOC_SITES = (
    "site:docs.unity3d.com OR site:forum.unity.com OR "
    "site:stackoverflow.com/questions/tagged/unity3d OR "
    "site:reddit.com/r/Unity3D OR site:blog.unity.com"
)


def register(mcp, config):
    """Register search and web fetch tools onto the MCP server."""
    api_key = config.brave_api_key

    @mcp.tool()
    async def brave_search(query: str, count: int = 5) -> str:
        """Search the web using the Brave Search API.
        Returns titles, URLs, and descriptions of top results.
        Use for finding tutorials, documentation, solutions, etc."""
        if not api_key:
            return "Error: BRAVE_API_KEY not configured. Set it in Claude Desktop env."
        if count > 20:
            count = 20
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": api_key,
                },
                params={"q": query, "count": count},
                timeout=15.0,
            )
            if resp.status_code != 200:
                return f"Search API error{resp.status_code}:{resp.text[:300]}"
            data = resp.json()

        results = data.get("web", {}).get("results", [])
        if not results:
            return f"No results found for:{query}"
        lines = [f"Search results for '{query}':", ""]
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            url = r.get("url", "")
            desc = r.get("description", "No description")[:200]
            lines.append(f"{i}.{title}\n{url}\n{desc}\n")
        return "\n".join(lines)

    @mcp.tool()
    async def search_unity_docs(query: str, count: int = 5) -> str:
        """Search specifically for Unity documentation and community resources.
        Searches docs.unity3d.com, Unity forums, Stack Overflow, Reddit,
        and the Unity blog. Great for API references and troubleshooting."""
        if not api_key:
            return "Error: BRAVE_API_KEY not configured."
        full_query = f"{query} ({UNITY_DOC_SITES})"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": api_key,
                },
                params={"q": full_query, "count": count},
                timeout=15.0,
            )
            if resp.status_code != 200:
                return f"Search error{resp.status_code}:{resp.text[:300]}"
            data = resp.json()

        results = data.get("web", {}).get("results", [])
        if not results:
            return f"No Unity docs found for:{query}"
        lines = [f"Unity documentation results for '{query}':", ""]
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            url = r.get("url", "")
            desc = r.get("description", "")[:250]
            lines.append(f"{i}.{title}\n{url}\n{desc}\n")
        return "\n".join(lines)

    @mcp.tool()
    async def fetch_url(url: str, max_length: int = 10000) -> str:
        """Fetch the text content of any web URL.
        Use this to read full Unity documentation pages, blog posts,
        changelogs, forum threads, or any web resource.
        Returns the first max_length characters of the page text."""
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=20.0
        ) as client:
            resp = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; UnityMCPServer/1.0)"
                },
            )
            if resp.status_code != 200:
                return f"Fetch error{resp.status_code} for{url}"
            content_type = resp.headers.get("content-type", "")
            if "text" not in content_type and "json" not in content_type:
                return f"Non-text content type:{content_type}. Cannot display."
            text = resp.text
            if len(text) > max_length:
                text = text[:max_length] + f"\n\n... [truncated at{max_length} chars]"
            return f"Content from{url}:\n\n{text}"