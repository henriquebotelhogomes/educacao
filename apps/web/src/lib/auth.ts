export type UserSession = {
  user_id: string;
  tenant_id: string;
  role: string;
  csrf_token: string;
  email?: string;
  display_name?: string;
};

export async function fetchCsrf(): Promise<string> {
  const response = await fetch("/api/v1/auth/csrf", { credentials: "include" });
  if (!response.ok) {
    throw new Error("Não foi possível obter o token de segurança CSRF.");
  }
  const data = (await response.json()) as { csrf_token: string };
  return data.csrf_token;
}

export async function signinUser(credentials: {
  email: string;
  password: string;
}): Promise<UserSession> {
  const csrf = await fetchCsrf();
  const response = await fetch("/api/v1/auth/signin", {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrf,
    },
    body: JSON.stringify(credentials),
  });

  if (!response.ok) {
    const errorData = (await response.json().catch(() => ({}))) as {
      detail?: string;
      message?: string;
    };
    throw new Error(errorData.detail ?? errorData.message ?? "Email ou senha incorretos.");
  }

  const session = (await response.json()) as UserSession;
  session.email = credentials.email;
  return session;
}

export async function signupUser(payload: {
  email: string;
  password: string;
  display_name: string;
}): Promise<UserSession> {
  const csrf = await fetchCsrf();
  const response = await fetch("/api/v1/auth/signup", {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrf,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = (await response.json().catch(() => ({}))) as {
      detail?: string;
      message?: string;
    };
    throw new Error(errorData.detail ?? errorData.message ?? "Não foi possível criar a conta.");
  }

  const session = (await response.json()) as UserSession;
  session.email = payload.email;
  session.display_name = payload.display_name;
  return session;
}

export async function logoutUser(): Promise<void> {
  try {
    const csrf = await fetchCsrf();
    await fetch("/api/v1/auth/logout", {
      method: "POST",
      credentials: "include",
      headers: {
        "X-CSRF-Token": csrf,
      },
    });
  } catch {
    // Session clearance continues
  }
}
