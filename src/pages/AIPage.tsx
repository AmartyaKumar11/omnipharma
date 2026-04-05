import { useState } from "react";
import { useAuth } from "@/auth/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Loader2, Sparkles, AlertCircle } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

type FormattedResponse = {
    type: string;
    title: string;
    columns?: string[];
    data?: any[];
    summary?: string;
    chart?: { x: any[]; y: any[] };
};

export function AIPage() {
    const { token } = useAuth();
    const [query, setQuery] = useState("");
    const [response, setResponse] = useState<FormattedResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const onAsk = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;
        setLoading(true);
        setError(null);
        setResponse(null);

        const base = import.meta.env.VITE_API_URL || "/api";
        try {
            const res = await fetch(`${base}/ai/query`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({ query })
            });
            if (!res.ok) {
                throw new Error(await res.text());
            }
            const data = await res.json();
            setResponse(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failure executing query.");
        } finally {
            setLoading(false);
        }
    };

    const renderTable = () => {
        if (!response?.data) return null;
        const cols = response.columns || (response.data.length > 0 ? Object.keys(response.data[0]) : []);

        // Safely handle empty datasets
        if (response.data.length === 0) {
            return <p className="text-sm font-medium">No records found matching this operation boundaries.</p>;
        }

        return (
            <div className="overflow-x-auto rounded-md border">
                <table className="w-full text-left text-sm">
                    <thead className="bg-muted">
                        <tr>
                            {cols.map((c) => <th key={c} className="p-3 font-semibold capitalize whitespace-nowrap">{c.replace(/_/g, " ")}</th>)}
                        </tr>
                    </thead>
                    <tbody>
                        {response.data.map((row, idx) => (
                            <tr key={idx} className="border-t">
                                {cols.map((c) => <td key={c} className="p-3 whitespace-nowrap">{row[c]}</td>)}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        );
    };

    const renderChart = () => {
        if (!response?.chart?.x || !response?.chart?.y) return <p className="text-sm text-destructive">Invalid chart data payload from API.</p>;
        const chartData = response.chart.x.map((xVal, i) => ({
            name: xVal,
            value: response.chart!.y[i]
        }));
        return (
            <div className="h-[350px] w-full pt-4">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <XAxis dataKey="name" stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
                        <YAxis stroke="#888888" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(v) => `${v}`} />
                        <Tooltip cursor={{ fill: 'transparent' }} contentStyle={{ borderRadius: '8px' }} />
                        <Bar dataKey="value" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        );
    };

    return (
        <div className="space-y-6">
            <Card className="border-primary/20 shadow-sm">
                <CardHeader className="bg-primary/5 pb-6">
                    <CardTitle className="flex items-center gap-2 text-primary">
                        <Sparkles className="h-5 w-5" />
                        AI Operations Associate
                    </CardTitle>
                    <CardDescription className="text-sm">
                        Powered by NVIDIA Kimi. Ask conversational questions securely filtered within your exact store boundary:
                    </CardDescription>
                </CardHeader>
                <CardContent className="pt-6">
                    <form onSubmit={onAsk} className="flex gap-3">
                        <Input
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="e.g. 'Show me low stock items' or 'store comparison'"
                            className="flex-1 shadow-sm border-primary/20 focus-visible:ring-primary/50"
                            disabled={loading}
                        />
                        <Button type="submit" disabled={loading} className="min-w-[120px] shadow-sm">
                            {loading ? (
                                <>
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    Thinking...
                                </>
                            ) : (
                                "Execute"
                            )}
                        </Button>
                    </form>
                    {error && (
                        <div className="mt-4 flex items-center gap-2 text-sm text-destructive font-medium bg-destructive/10 p-3 rounded-md">
                            <AlertCircle className="h-4 w-4" />
                            {error}
                        </div>
                    )}
                </CardContent>
            </Card>

            {response && (
                <Card className="shadow-sm border-border">
                    <CardHeader>
                        <CardTitle className="text-xl tracking-tight">{response.title}</CardTitle>
                        {response.summary && response.type !== "card" && (
                            <CardDescription className="text-sm text-foreground/80 font-medium">
                                {response.summary}
                            </CardDescription>
                        )}
                    </CardHeader>
                    <CardContent className="pt-0">
                        {response.type === "card" && (
                            <div className="rounded-lg bg-primary/10 border border-primary/20 p-5 text-sm font-medium leading-relaxed">
                                <Sparkles className="h-4 w-4 inline-block mr-2 text-primary -mt-1" />
                                {response.summary || "No insights mapped."}
                            </div>
                        )}
                        {response.type === "table" && renderTable()}
                        {response.type === "chart" && renderChart()}
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
