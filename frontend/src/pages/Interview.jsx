import { useEffect, useState, useRef } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import FeedbackCard from "../components/FeedbackCard";
import {
  buildAnswerMetrics,
  clearInterviewState,
  loadInterviewState,
  saveInterviewState,
  submitAnswer
} from "../lib/api";

function Interview() {
  const navigate = useNavigate();
  const location = useLocation();
  const { sessionId } = useParams();
  const persistedState = loadInterviewState();
  const initialState = location.state || persistedState;

  const [question, setQuestion] = useState(initialState?.question || "");
  const [difficulty, setDifficulty] = useState(initialState?.difficulty || "medium");
  const [round, setRound] = useState(initialState?.round || 1);
  const [elo, setElo] = useState(initialState?.elo || 1200);
  const [skill] = useState(initialState?.skill || persistedState?.skill || "");
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState(null);
  const [lastScore, setLastScore] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [timeLeft, setTimeLeft] = useState(180);
  const [isListening, setIsListening] = useState(false);
  const [animationKey, setAnimationKey] = useState(0);
  const recognitionRef = useRef(null);

  useEffect(() => {
    if (typeof window !== "undefined" && ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;

      recognition.onresult = (event) => {
        let finalTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript + ' ';
          }
        }
        if (finalTranscript) {
          setAnswer((prev) => prev + (prev.trim() ? ' ' : '') + finalTranscript.trim() + ' ');
        }
      };

      recognition.onerror = (event) => {
        if (event.error === 'not-allowed') {
          setError("Microphone access denied.");
          setIsListening(false);
        }
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }
  }, []);

  const toggleListening = () => {
    if (isListening) {
      recognitionRef.current?.stop();
    } else {
      if (recognitionRef.current) {
        recognitionRef.current.start();
        setIsListening(true);
      } else {
        setError("Speech Recognition is not supported in this browser. Try Chrome/Safari.");
      }
    }
  };

  useEffect(() => {
    if (timeLeft <= 0) {
      if (!isSubmitting && !feedback) {
        handleSubmit();
      }
      return;
    }
    
    if (feedback) return;

    const timer = setInterval(() => {
      setTimeLeft(prev => prev - 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [timeLeft, isSubmitting, feedback]);

  useEffect(() => {
    setTimeLeft(180);
  }, [round]);

  useEffect(() => {
    if (!sessionId || !initialState?.question) {
      navigate("/", { replace: true });
    }
  }, [initialState?.question, navigate, sessionId]);

  async function handleSubmit(event) {
    if (event?.preventDefault) {
      event.preventDefault();
    }
    const finalAnswer = answer.trim() || "No answer provided within time limit.";

    const metrics = buildAnswerMetrics(question, finalAnswer);
    setIsSubmitting(true);
    setError("");

    try {
      const response = await submitAnswer({
        session_id: sessionId,
        round,
        answer_text: finalAnswer,
        engagement_label: "Text mode",
        wpm: 0,
        pause_count: 0,
        ...metrics
      });

      setFeedback(response.feedback);
      setLastScore(response.final_score);
      setElo(response.elo_after || elo);

      if (response.next_question) {
        const nextState = {
          ...(persistedState || {}),
          sessionId,
          question: response.next_question,
          difficulty: response.next_difficulty,
          round: round + 1,
          elo: response.elo_after || elo,
          skill
        };
        saveInterviewState(nextState);
        setQuestion(response.next_question);
        setDifficulty(response.next_difficulty);
        setRound((current) => current + 1);
        setAnswer("");
        setAnimationKey((prev) => prev + 1);
      } else {
        clearInterviewState();
        navigate(`/dashboard/${sessionId}`);
      }
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  const wordCount = answer.trim() ? answer.trim().split(/\s+/).length : 0;

  return (
    <div className="app-shell">
      <div className="mb-6 flex flex-col gap-4 rounded-[28px] bg-ink p-6 text-white sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.24em] text-white/65">Interview in progress</p>
          <h1 className="mt-3 text-4xl font-bold">{skill || "Adaptive technical interview"}</h1>
          <p className="mt-2 text-sm text-white/70">
            Round {round} • Difficulty {difficulty}
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="rounded-[24px] bg-white/10 px-5 py-4 text-right">
            <p className="text-xs uppercase tracking-[0.18em] text-white/60">Running Elo</p>
            <p className="mt-1 text-3xl font-bold">{Math.round(elo)}</p>
          </div>
          <div className="rounded-[24px] border border-white/10 px-5 py-4 text-right">
            <p className="text-xs uppercase tracking-[0.18em] text-white/60">Mode</p>
            <p className="mt-1 text-sm font-semibold text-white">Text answer only</p>
          </div>
          <div className="rounded-[24px] border border-white/10 px-5 py-4 text-right">
            <p className="text-xs uppercase tracking-[0.18em] text-white/60">Time Left</p>
            <p className={`mt-1 text-2xl font-bold ${timeLeft <= 30 && !feedback ? "text-ember animate-pulse" : "text-white"}`}>
              {Math.floor(timeLeft / 60)}:{String(timeLeft % 60).padStart(2, '0')}
            </p>
          </div>
        </div>
      </div>

      <div key={animationKey} className="grid gap-6 transition-all duration-700 ease-in-out lg:grid-cols-[1.15fr_0.85fr] opacity-100 animate-[fadeIn_0.5s_ease-in-out]">
        <section className="glass-panel p-8">
          <div className="mb-6">
            <p className="section-title">Current Prompt</p>
            <h2 className="mt-3 text-3xl font-bold leading-tight">{question}</h2>
          </div>

          <form className="space-y-5" onSubmit={handleSubmit}>
            <div>
              <label className="field-label" htmlFor="answer">
                Your answer
              </label>
              <textarea
                id="answer"
                className="field-input min-h-[220px] resize-y"
                placeholder="Type your answer here. Voice capture is planned for Month 2."
                value={answer}
                onChange={(event) => setAnswer(event.target.value)}
              />
            </div>

            <div className="flex flex-wrap items-center gap-3 text-sm text-ink/70">
              <span className="chip border-ink/10 bg-mist/80">Words {wordCount}</span>
              <span className="chip border-ink/10 bg-mist/80">Difficulty {difficulty}</span>
              <span className="chip border-ink/10 bg-mist/80">Adaptive round {round}</span>
              {isListening && <span className="chip bg-ember/10 border-ember/20 text-ember animate-pulse">● Recording...</span>}
            </div>

            {error ? (
              <div className="rounded-2xl border border-ember/20 bg-ember/10 px-4 py-3 text-sm text-ember">
                {error}
              </div>
            ) : null}

            <div className="flex items-center gap-3">
              <button className="primary-button" disabled={isSubmitting} type="submit">
                {isSubmitting ? "Scoring answer..." : "Submit answer"}
              </button>
              <button 
                type="button"
                onClick={toggleListening}
                className={`rounded-[100px] border px-6 py-3.5 text-sm font-semibold transition-all ${isListening ? 'border-ember text-ember bg-ember/5 hover:bg-ember/10' : 'border-ink/20 text-ink hover:bg-mist'}`}
              >
                {isListening ? "Stop Recording" : "Enable Microphone"}
              </button>
            </div>
          </form>
        </section>

        <FeedbackCard feedback={feedback} score={lastScore} />
      </div>
    </div>
  );
}

export default Interview;
