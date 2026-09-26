import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { apiClient } from "../lib/api/client";

// 401応答時のログインページへのリダイレクト挙動

const setLocation = (pathname: string, search: string) => {
  const location = { pathname, search, href: `http://album.local${pathname}${search}` };
  vi.stubGlobal("window", { location });
  return location;
};

describe("apiClient 401 redirect", () => {
  beforeEach(() => {
    vi.stubGlobal("localStorage", { getItem: () => "expired-token" });
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(null, { status: 401, statusText: "Unauthorized" })),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("ログインページ以外では元のパスをredirectに付けてログインページへ遷移する", async () => {
    const location = setLocation("/photo/detail/abc", "?x=1");

    await expect(apiClient.get("/users/me")).rejects.toMatchObject({ status: 401 });

    expect(location.href).toBe(`/login?redirect=${encodeURIComponent("/photo/detail/abc?x=1")}`);
  });

  it("ログインページでは遷移せず、?name=&pass= を保持する", async () => {
    const location = setLocation("/login", "?name=admin&pass=admin");
    const before = location.href;

    await expect(apiClient.get("/users/me")).rejects.toMatchObject({ status: 401 });

    expect(location.href).toBe(before);
  });
});
