export default async function GapSentinel(ctx) {
    const bridgeUrl = "http://127.0.0.1:11436";

    return {
        "permission.ask": async (permission, output) => {
            // 1. Identify the action (usually tool execution)
            const action = permission.type === "tool" ? "write" : "read";

            console.log(`[*] GAP Sentinel: Vetting ${action} on ${permission.title}...`);

            // 2. Query the IntelHub Bridge
            try {
                const resp = await fetch(`${bridgeUrl}/v1/guard/check`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        action: action,
                        resource: "filesystem",
                        metadata: permission.metadata
                    })
                });

                const result = await resp.json();

                if (result.allowed) {
                    console.log(`[+] GAP Sentinel: AUTHORIZED.`);
                    output.status = "allow";
                } else {
                    console.warn(`[!] GAP Sentinel: BLOCKED. Reason: ${result.reason}`);
                    // 'ask' triggers the OpenCode native Allow/Deny UI
                    output.status = "ask";
                }
            } catch (e) {
                console.error("[-] GAP Sentinel Bridge Connectivity Error:", e);
                output.status = "ask"; // Safety fallback
            }
        },

        "experimental.chat.system.transform": async (input, output) => {
            // Injects Sovereign Mode into the agent's context
            try {
                const resp = await fetch(`${bridgeUrl}/health`);
                const health = await resp.json();
                if (health.status === "healthy") {
                    output.system.unshift("You are operating within the Sovereign IntelHub. All actions are monitored by the GAP Protocol Sentinel.");
                }
            } catch (e) { }
        }
    };
}
