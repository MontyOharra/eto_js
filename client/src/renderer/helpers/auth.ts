const AUTH_KEY = "eto_is_authenticated";

export function isAuthenticated(): boolean {
  try {
    return sessionStorage.getItem(AUTH_KEY) === "1";
  } catch {
    return false;
  }
}

export function setAuthenticated(value: boolean): void {
  try {
    if (value) {
      sessionStorage.setItem(AUTH_KEY, "1");
    } else {
      sessionStorage.removeItem(AUTH_KEY);
    }
  } catch {
    // ignore
  }
}
