import { createContext, useContext } from "react";

export type UiLang = "fr" | "ar" | "en";

type Dict = Record<string, string>;

const fr: Dict = {
  "app.name": "Assistant Administratif Tunisien",
  "app.newConversation": "Nouvelle conversation",
  "theme.toggle": "Changer de thème",
  "lang.switch": "Changer la langue",
  "input.placeholder": "Posez votre question sur le droit du travail ou la CNSS…",
  "input.send": "Envoyer",
  "input.stop": "Arrêter",
  "input.hint": "Entrée pour envoyer, Maj+Entrée pour une nouvelle ligne",
  "empty.title": "Comment puis-je vous aider ?",
  "empty.subtitle": "Posez une question sur le droit du travail tunisien ou la CNSS.",
  "empty.examplesFr": "Exemples en français",
  "empty.examplesAr": "Exemples en arabe",
  "warming.message": "Préparation du modèle, la première question peut prendre un moment…",
  "sources.title": "Sources",
  "sources.other": "Autres sources consultées",
  "sources.score": "Score de pertinence",
  "refusal.title": "Aucune réponse trouvée dans les documents",
  "refusal.no_sources": "Aucun document pertinent n'a été trouvé pour cette question.",
  "refusal.below_threshold": "La question semble hors du champ des documents disponibles.",
  "refusal.model_declined": "La question semble hors du champ des documents disponibles.",
  "refusal.empty_answer": "Le modèle n'a pas pu formuler de réponse à partir des documents.",
  "error.validation": "Veuillez vérifier votre question (entre 3 et 1000 caractères).",
  "error.serviceUnavailable": "Service temporairement indisponible. Veuillez réessayer.",
  "error.network": "Impossible de contacter le serveur. Vérifiez votre connexion et réessayez.",
  "error.retry": "Réessayer",
  "timings.summary": "Premier mot en {first}s, total {total}s",
  "footer.disclaimer":
    "Outil informatif basé sur les documents fournis. Ne constitue pas un avis juridique. Vérifiez toujours auprès de la source officielle.",
};

const ar: Dict = {
  "app.name": "المساعد الإداري التونسي",
  "app.newConversation": "محادثة جديدة",
  "theme.toggle": "تبديل المظهر",
  "lang.switch": "تغيير اللغة",
  "input.placeholder": "اطرح سؤالك حول قانون الشغل أو الصندوق القومي للضمان الاجتماعي…",
  "input.send": "إرسال",
  "input.stop": "إيقاف",
  "input.hint": "Enter للإرسال، Shift+Enter لسطر جديد",
  "empty.title": "كيف يمكنني مساعدتك؟",
  "empty.subtitle": "اطرح سؤالاً حول قانون الشغل التونسي أو الصندوق القومي للضمان الاجتماعي.",
  "empty.examplesFr": "أمثلة بالفرنسية",
  "empty.examplesAr": "أمثلة بالعربية",
  "warming.message": "جاري تحضير النموذج، قد يستغرق السؤال الأول بعض الوقت…",
  "sources.title": "المصادر",
  "sources.other": "مصادر أخرى تم فحصها",
  "sources.score": "درجة الصلة",
  "refusal.title": "لم يتم العثور على إجابة في الوثائق",
  "refusal.no_sources": "لم يتم العثور على وثائق ذات صلة بهذا السؤال.",
  "refusal.below_threshold": "يبدو أن السؤال خارج نطاق الوثائق المتوفرة.",
  "refusal.model_declined": "يبدو أن السؤال خارج نطاق الوثائق المتوفرة.",
  "refusal.empty_answer": "تعذر على النموذج صياغة إجابة بناءً على الوثائق.",
  "error.validation": "يرجى التحقق من سؤالك (بين 3 و 1000 حرف).",
  "error.serviceUnavailable": "الخدمة غير متوفرة حالياً. يرجى المحاولة مرة أخرى.",
  "error.network": "تعذر الاتصال بالخادم. تحقق من اتصالك وحاول مرة أخرى.",
  "error.retry": "إعادة المحاولة",
  "timings.summary": "أول كلمة في {first} ثانية، الإجمالي {total} ثانية",
  "footer.disclaimer":
    "أداة إعلامية تعتمد على الوثائق المقدمة. لا تُعد استشارة قانونية. يرجى دائماً التحقق من المصدر الرسمي.",
};

const en: Dict = {
  "app.name": "Tunisian Admin Assistant",
  "app.newConversation": "New conversation",
  "theme.toggle": "Toggle theme",
  "lang.switch": "Switch language",
  "input.placeholder": "Ask about labor law or CNSS social security…",
  "input.send": "Send",
  "input.stop": "Stop",
  "input.hint": "Enter to send, Shift+Enter for a new line",
  "empty.title": "How can I help?",
  "empty.subtitle": "Ask a question about Tunisian labor law or CNSS.",
  "empty.examplesFr": "French examples",
  "empty.examplesAr": "Arabic examples",
  "warming.message": "Warming up the model, the first question can take a moment…",
  "sources.title": "Sources",
  "sources.other": "Other sources considered",
  "sources.score": "Relevance score",
  "refusal.title": "No answer found in the documents",
  "refusal.no_sources": "No relevant documents were found for this question.",
  "refusal.below_threshold": "The question seems outside the available documents.",
  "refusal.model_declined": "The question seems outside the available documents.",
  "refusal.empty_answer": "The model could not form an answer from the documents.",
  "error.validation": "Please check your question (3 to 1000 characters).",
  "error.serviceUnavailable": "Service temporarily unavailable. Please try again.",
  "error.network": "Could not reach the server. Check your connection and try again.",
  "error.retry": "Retry",
  "timings.summary": "First word in {first}s, total {total}s",
  "footer.disclaimer":
    "Informational tool based on the provided documents. Not legal advice. Always verify with the official source.",
};

const dicts: Record<UiLang, Dict> = { fr, ar, en };

export function t(key: string, lang: UiLang, vars?: Record<string, string>): string {
  let value = dicts[lang][key] ?? dicts.fr[key] ?? key;
  if (vars) {
    for (const [name, replacement] of Object.entries(vars)) {
      value = value.replace(`{${name}}`, replacement);
    }
  }
  return value;
}

const STORAGE_KEY = "lang";

export function loadStoredLang(): UiLang {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "fr" || stored === "ar" || stored === "en") return stored;
  } catch {
    // localStorage unavailable (private mode, etc.) - fall back to default.
  }
  return "fr";
}

export function storeLang(lang: UiLang): void {
  try {
    localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    // Ignore - per-viewer convenience only.
  }
}

export interface LangContextValue {
  lang: UiLang;
  setLang: (lang: UiLang) => void;
  t: (key: string, vars?: Record<string, string>) => string;
}

export const LangContext = createContext<LangContextValue | null>(null);

export function useLang(): LangContextValue {
  const ctx = useContext(LangContext);
  if (!ctx) throw new Error("useLang must be used within a LangContext provider.");
  return ctx;
}
