import { cookies } from "next/headers";

export const ACCESS_COOKIE = "clip_access";
export const REFRESH_COOKIE = "clip_refresh";

const isProd = process.env.NODE_ENV === "production";

/**
 * Store the JWTs as httpOnly cookies (never readable by client JS), so tokens
 * are not exposed to XSS the way localStorage would be.
 */
export function setAuthCookies(accessToken: string, refreshToken: string) {
  const store = cookies();
  const base = {
    httpOnly: true,
    secure: isProd,
    sameSite: "lax" as const,
    path: "/",
  };
  // Access token: short-lived; refresh token: longer-lived.
  store.set(ACCESS_COOKIE, accessToken, { ...base, maxAge: 60 * 30 });
  store.set(REFRESH_COOKIE, refreshToken, { ...base, maxAge: 60 * 60 * 24 * 7 });
}

export function clearAuthCookies() {
  const store = cookies();
  store.delete(ACCESS_COOKIE);
  store.delete(REFRESH_COOKIE);
}
