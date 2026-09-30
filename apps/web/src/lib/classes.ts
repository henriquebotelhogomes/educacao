export type PedagogicalMode = "EXPLANATION" | "SOCRATIC";
export type ClassroomRole = "STUDENT" | "EDUCATOR" | "ADMIN";

export type Classroom = {
  id: string;
  name: string;
  code: string;
  subject: string | null;
  knowledge_base_id: string;
  pedagogical_mode: PedagogicalMode;
  created_by_user_id: string;
  created_at: string;
  my_role: ClassroomRole;
};

export type ClassroomMember = {
  user_id: string;
  role: ClassroomRole;
  joined_at: string;
};

export type LearningGapMetric = {
  topic: string;
  query_count: number;
  gap_score: number;
  last_occurred_at: string;
};

export type StudentFlashcard = {
  id: string;
  classroom_id: string;
  user_id: string;
  concept: string;
  explanation: string;
  mastery_level: number;
  review_count: number;
  last_reviewed_at: string | null;
  created_at: string;
};

export async function fetchCsrfToken(): Promise<string> {
  const response = await fetch("/api/v1/auth/csrf", { credentials: "include" });
  if (!response.ok) {
    throw new Error("Falha ao obter token de segurança CSRF.");
  }
  const data = (await response.json()) as { csrf_token: string };
  return data.csrf_token;
}

export async function listClassrooms(): Promise<Classroom[]> {
  const response = await fetch("/api/v1/classes", { credentials: "include" });
  if (response.status === 401) {
    throw new Error("Faça login para acessar suas turmas.");
  }
  if (!response.ok) {
    throw new Error("Não foi possível carregar as turmas.");
  }
  return (await response.json()) as Classroom[];
}

export async function joinClassroom(code: string): Promise<Classroom> {
  const csrf = await fetchCsrfToken();
  const response = await fetch("/api/v1/classes/join", {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrf,
    },
    body: JSON.stringify({ code: code.trim().toUpperCase() }),
  });
  if (!response.ok) {
    const errorData = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(errorData.detail ?? "Não foi possível entrar na turma. Verifique o código.");
  }
  return (await response.json()) as Classroom;
}

export async function createClassroom(payload: {
  name: string;
  subject?: string;
  pedagogical_mode?: PedagogicalMode;
}): Promise<Classroom> {
  const csrf = await fetchCsrfToken();
  const response = await fetch("/api/v1/classes", {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrf,
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const errorData = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(errorData.detail ?? "Erro ao criar turma.");
  }
  return (await response.json()) as Classroom;
}

export async function getClassroom(id: string): Promise<Classroom> {
  const response = await fetch(`/api/v1/classes/${id}`, { credentials: "include" });
  if (!response.ok) {
    throw new Error("Turma não encontrada.");
  }
  return (await response.json()) as Classroom;
}

export async function updateClassroom(
  id: string,
  payload: { name?: string; pedagogical_mode?: PedagogicalMode }
): Promise<Classroom> {
  const csrf = await fetchCsrfToken();
  const response = await fetch(`/api/v1/classes/${id}`, {
    method: "PATCH",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrf,
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("Falha ao atualizar configurações da turma.");
  }
  return (await response.json()) as Classroom;
}

export async function listClassroomMembers(id: string): Promise<ClassroomMember[]> {
  const response = await fetch(`/api/v1/classes/${id}/members`, { credentials: "include" });
  if (!response.ok) {
    throw new Error("Falha ao listar membros da turma.");
  }
  return (await response.json()) as ClassroomMember[];
}

export async function getLearningGapRadar(id: string): Promise<LearningGapMetric[]> {
  const response = await fetch(`/api/v1/classes/${id}/radar`, { credentials: "include" });
  if (!response.ok) {
    throw new Error("Falha ao obter métricas de radar.");
  }
  return (await response.json()) as LearningGapMetric[];
}

export async function listStudentFlashcards(classroomId: string): Promise<StudentFlashcard[]> {
  const response = await fetch(`/api/v1/classes/${classroomId}/flashcards`, { credentials: "include" });
  if (!response.ok) {
    throw new Error("Falha ao carregar flashcards.");
  }
  return (await response.json()) as StudentFlashcard[];
}

export async function createStudentFlashcard(
  classroomId: string,
  payload: { concept: string; explanation: string }
): Promise<StudentFlashcard> {
  const csrf = await fetchCsrfToken();
  const response = await fetch(`/api/v1/classes/${classroomId}/flashcards`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrf,
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("Falha ao criar flashcard.");
  }
  return (await response.json()) as StudentFlashcard;
}

export async function updateFlashcardMastery(
  classroomId: string,
  flashcardId: string,
  masteryLevel: number
): Promise<StudentFlashcard> {
  const csrf = await fetchCsrfToken();
  const response = await fetch(`/api/v1/classes/${classroomId}/flashcards/${flashcardId}`, {
    method: "PATCH",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrf,
    },
    body: JSON.stringify({ mastery_level: masteryLevel }),
  });
  if (!response.ok) {
    throw new Error("Falha ao atualizar nível do flashcard.");
  }
  return (await response.json()) as StudentFlashcard;
}
