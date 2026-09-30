"use client";

import { FormEvent, use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Classroom,
  StudentFlashcard,
  createStudentFlashcard,
  getClassroom,
  listStudentFlashcards,
  updateFlashcardMastery,
} from "@/lib/classes";

export default function StudentFlashcardsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: classroomId } = use(params);
  const [classroom, setClassroom] = useState<Classroom | null>(null);
  const [flashcards, setFlashcards] = useState<StudentFlashcard[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newConcept, setNewConcept] = useState("");
  const [newExplanation, setNewExplanation] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [cls, cards] = await Promise.all([
        getClassroom(classroomId),
        listStudentFlashcards(classroomId),
      ]);
      setClassroom(cls);
      setFlashcards(cards);
    } catch {
      setStatusMessage("Erro ao carregar flashcards.");
    } finally {
      setLoading(false);
    }
  }, [classroomId]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  async function handleMasteryUpdate(flashcardId: string, newLevel: number) {
    try {
      const updated = await updateFlashcardMastery(classroomId, flashcardId, Math.max(0, newLevel));
      setFlashcards((prev) =>
        prev.map((card) => (card.id === flashcardId ? updated : card))
      );
      setIsFlipped(false);
      // Move to next card if available
      if (currentIndex < flashcards.length - 1) {
        setCurrentIndex((i) => i + 1);
      }
    } catch {
      setStatusMessage("Falha ao atualizar nível do cartão.");
    }
  }

  async function handleCreateCard(e: FormEvent) {
    e.preventDefault();
    if (!newConcept.trim() || !newExplanation.trim()) return;

    try {
      setIsSaving(true);
      const created = await createStudentFlashcard(classroomId, {
        concept: newConcept.trim(),
        explanation: newExplanation.trim(),
      });
      setFlashcards((prev) => [created, ...prev]);
      setNewConcept("");
      setNewExplanation("");
      setShowCreateModal(false);
      setStatusMessage("Novo flashcard adicionado ao seu deck!");
      setTimeout(() => setStatusMessage(null), 3000);
    } catch {
      setStatusMessage("Erro ao criar flashcard.");
    } finally {
      setIsSaving(false);
    }
  }

  const currentCard = flashcards[currentIndex];

  function getMasteryBadge(level: number) {
    if (level >= 5) {
      return { text: "⭐⭐ Dominado", color: "bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800" };
    }
    if (level >= 3) {
      return { text: "⭐ Bom", color: "bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-800" };
    }
    if (level >= 1) {
      return { text: "Em Aprendizado", color: "bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800" };
    }
    return { text: "Novato", color: "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700" };
  }

  return (
    <main className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-1">
            <Link href="/classes" className="hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors">
              ← Minhas Turmas
            </Link>
            <span>/</span>
            <span>{classroom ? classroom.name : "..."}</span>
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white flex items-center gap-2">
            <span>🃏 Meus Flashcards de Estudo</span>
          </h1>
          <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
            Fixação ativa com repetição espaçada personalizada para esta turma.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href={`/classes/${classroomId}/tutor`}
            className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-xs transition-colors"
          >
            💬 Abrir Tutor
          </Link>
          <button
            onClick={() => setShowCreateModal(true)}
            type="button"
            className="px-3.5 py-1.5 rounded-lg bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold border border-slate-300 dark:border-slate-700 transition-colors shadow-2xs"
          >
            ➕ Novo Cartão
          </button>
        </div>
      </div>

      {statusMessage && (
        <div role="status" className="p-3 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs text-slate-800 dark:text-slate-300">
          {statusMessage}
        </div>
      )}

      {/* Main Flashcard Interactive Area */}
      {loading ? (
        <div className="text-center py-16 text-slate-500 text-sm">Carregando seu deck...</div>
      ) : flashcards.length === 0 ? (
        <div className="text-center py-16 rounded-2xl border border-dashed border-slate-300 dark:border-slate-800 p-8 space-y-3 bg-white dark:bg-transparent">
          <span className="text-4xl block">🃏</span>
          <p className="text-slate-800 dark:text-slate-300 font-medium">Você ainda não tem flashcards salvos para esta turma.</p>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Ao conversar com o tutor na turma, clique no botão &ldquo;Salvar como Flashcard&rdquo; em qualquer resposta para adicioná-la aqui, ou crie cartões manualmente.
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            type="button"
            className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-sm"
          >
            Criar Primeiro Flashcard
          </button>
        </div>
      ) : currentCard ? (
        <div className="space-y-6">
          {/* Progress bar / Counter */}
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>
              Cartão <strong>{currentIndex + 1}</strong> de <strong>{flashcards.length}</strong>
            </span>
            <div className="flex items-center gap-1.5">
              {flashcards.map((card, i) => (
                <button
                  key={card.id}
                  onClick={() => {
                    setCurrentIndex(i);
                    setIsFlipped(false);
                  }}
                  className={`w-2.5 h-2.5 rounded-full transition-all ${
                    i === currentIndex ? "bg-indigo-600 scale-125" : "bg-slate-300 dark:bg-slate-800 hover:bg-slate-400 dark:hover:bg-slate-700"
                  }`}
                  title={`Ir para cartão ${i + 1}`}
                  type="button"
                />
              ))}
            </div>
          </div>

          {/* Interactive Flip Card */}
          <div className="perspective-1000 w-full min-h-[300px]">
            <div
              onClick={() => setIsFlipped(!isFlipped)}
              className={`cursor-pointer w-full min-h-[300px] rounded-2xl border p-8 transition-transform duration-500 flex flex-col justify-between shadow-sm dark:shadow-2xl ${
                isFlipped
                  ? "bg-white dark:bg-slate-900 border-indigo-500 dark:border-indigo-600/60 ring-2 ring-indigo-500/20"
                  : "bg-white dark:bg-slate-900/90 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
              }`}
            >
              {/* Card Header */}
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  {isFlipped ? "Verso — Resposta / Explicação" : "Frente — Conceito / Pergunta"}
                </span>
                <span
                  className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold border ${
                    getMasteryBadge(currentCard.mastery_level).color
                  }`}
                >
                  {getMasteryBadge(currentCard.mastery_level).text} (Nível {currentCard.mastery_level})
                </span>
              </div>

              {/* Card Content */}
              <div className="py-6 my-auto text-center">
                <p className="text-lg sm:text-xl font-medium text-slate-900 dark:text-white leading-relaxed">
                  {isFlipped ? currentCard.explanation : currentCard.concept}
                </p>
                <span className="text-xs text-slate-400 dark:text-slate-500 block mt-4">
                  {isFlipped ? "Toque para voltar à pergunta" : "Toque ou clique para virar e ver a resposta 🔄"}
                </span>
              </div>

              {/* Card Footer */}
              <div className="text-[11px] text-slate-400 dark:text-slate-500 flex items-center justify-between border-t border-slate-100 dark:border-slate-800/80 pt-3">
                <span>Revisado {currentCard.review_count} vezes</span>
                <span>
                  Criado em: {new Date(currentCard.created_at).toLocaleDateString("pt-BR")}
                </span>
              </div>
            </div>
          </div>

          {/* Mastery Rating Buttons (visible when flipped) */}
          {isFlipped && (
            <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 shadow-xs">
              <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                Como foi sua lembrança deste conceito?
              </span>
              <div className="flex gap-2 w-full sm:w-auto">
                <button
                  onClick={() => void handleMasteryUpdate(currentCard.id, 0)}
                  type="button"
                  className="flex-1 sm:flex-none px-4 py-2 rounded-xl bg-red-50 hover:bg-red-100 dark:bg-red-950/80 dark:hover:bg-red-900 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-200 text-xs font-semibold transition-colors"
                >
                  🔄 Preciso Revisar (Nível 0)
                </button>
                <button
                  onClick={() => void handleMasteryUpdate(currentCard.id, currentCard.mastery_level + 1)}
                  type="button"
                  className="flex-1 sm:flex-none px-4 py-2 rounded-xl bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/80 dark:hover:bg-emerald-900 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-200 text-xs font-semibold transition-colors"
                >
                  ⭐ Acertei (+1 Nível)
                </button>
              </div>
            </div>
          )}

          {/* Next / Previous Controls */}
          <div className="flex items-center justify-between pt-2">
            <button
              onClick={() => {
                if (currentIndex > 0) {
                  setCurrentIndex((i) => i - 1);
                  setIsFlipped(false);
                }
              }}
              disabled={currentIndex === 0}
              type="button"
              className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 disabled:opacity-30 text-slate-700 dark:text-white text-xs font-medium border border-slate-200 dark:border-slate-700 transition-colors"
            >
              ← Cartão Anterior
            </button>

            <button
              onClick={() => setIsFlipped(!isFlipped)}
              type="button"
              className="px-5 py-2 rounded-xl bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-600/30 dark:hover:bg-indigo-600/50 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/40 text-xs font-semibold transition-colors"
            >
              Virar Cartão 🔄
            </button>

            <button
              onClick={() => {
                if (currentIndex < flashcards.length - 1) {
                  setCurrentIndex((i) => i + 1);
                  setIsFlipped(false);
                }
              }}
              disabled={currentIndex === flashcards.length - 1}
              type="button"
              className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 disabled:opacity-30 text-slate-700 dark:text-white text-xs font-medium border border-slate-200 dark:border-slate-700 transition-colors"
            >
              Próximo Cartão →
            </button>
          </div>
        </div>
      ) : null}

      {/* Modal: Create Flashcard */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 max-w-lg w-full space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <h3 className="text-base font-bold text-slate-900 dark:text-white">Criar Novo Flashcard</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                type="button"
                className="text-slate-400 hover:text-slate-600 dark:hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateCard} className="space-y-4">
              <div>
                <label htmlFor="cardConcept" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Frente: Pergunta ou Conceito Chave *
                </label>
                <input
                  id="cardConcept"
                  type="text"
                  required
                  value={newConcept}
                  onChange={(e) => setNewConcept(e.target.value)}
                  placeholder="Ex: O que é fixação biológica de nitrogênio?"
                  className="w-full px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label htmlFor="cardExplanation" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Verso: Resposta ou Explicação *
                </label>
                <textarea
                  id="cardExplanation"
                  rows={4}
                  required
                  value={newExplanation}
                  onChange={(e) => setNewExplanation(e.target.value)}
                  placeholder="Ex: Processo realizado por bactérias simbióticas (como Rhizobium) que convertem N2 atmosférico em amônia (NH3) utilizável pelas plantas."
                  className="w-full p-3 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs border border-slate-200 dark:border-slate-700"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold shadow-xs"
                >
                  {isSaving ? "Salvando..." : "Salvar Flashcard"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}
