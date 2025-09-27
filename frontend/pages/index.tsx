import Head from "next/head";
import { useHealthStatus } from "@/hooks/useHealthStatus";

export default function Home() {
  const { healthStatus, loading, error } = useHealthStatus();

  return (
    <>
      <Head>
        <title>Family Album</title>
        <meta name="description" content="家族のアルバムアプリ" />
      </Head>
      <main>
        <h1>Welcome to Family Album</h1>
        <div
          style={{
            marginTop: "20px",
            padding: "10px",
            border: "1px solid #ccc",
            borderRadius: "5px",
          }}
        >
          <h2>Backend Health Status</h2>
          {loading && <p>Loading health status...</p>}
          {error && <p style={{ color: "red" }}>Error: {error}</p>}
          {healthStatus && (
            <div>
              <p>
                <strong>Status:</strong>{" "}
                <span
                  style={{
                    color: healthStatus.status === "ok" ? "green" : "red",
                  }}
                >
                  {healthStatus.status}
                </span>
              </p>
              <p>
                <strong>Message:</strong> {healthStatus.message}
              </p>
            </div>
          )}
        </div>
      </main>
    </>
  );
}
