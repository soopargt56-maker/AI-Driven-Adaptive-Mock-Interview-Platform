function FeedbackCard({ feedback, score }) {
  if (!feedback) {
    return null;
  }

  const content = feedback.content || [];
  const strengths = feedback.strengths || [];

  return (
    <div className="glass-panel h-full p-6 animate-[fadeIn_0.6s_ease-out] shadow-[0_8px_32px_rgba(0,0,0,0.1)] backdrop-blur-xl bg-white/40 border-white/40 dark:bg-ink/40 dark:border-white/10">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="section-title text-ocean">Round Feedback</p>
          <h3 className="mt-2 text-2xl font-bold bg-gradient-to-r from-ocean to-moss bg-clip-text text-transparent">C4 Response Review</h3>
        </div>
        <div className="rounded-full bg-ember/10 px-4 py-2 text-sm font-semibold text-ember">
          Score {score ?? "--"}
        </div>
      </div>

      <div className="space-y-4 text-sm text-ink/75">
        <div>
          <p className="mb-2 font-semibold text-ink">Content</p>
          <div className="space-y-2">
            {content.length ? (
              content.map((item) => (
                <p key={item} className="rounded-2xl bg-mist/80 px-4 py-3">
                  {item}
                </p>
              ))
            ) : (
              <p className="rounded-2xl bg-mist/80 px-4 py-3">
                Submit an answer to see structured feedback.
              </p>
            )}
          </div>
        </div>

        <div>
          <p className="mb-2 font-semibold text-ink">Strengths</p>
          <div className="flex flex-wrap gap-2">
            {strengths.length ? (
              strengths.map((item) => (
                <span key={item} className="chip bg-moss/10 text-moss">
                  {item}
                </span>
              ))
            ) : (
              <span className="chip">Awaiting assessment</span>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-ocean/10 bg-ocean/5 px-4 py-4">
          <p className="mb-1 font-semibold text-ocean">Next Step</p>
          <p>{feedback.next_step || "Keep going. The next recommendation will appear here."}</p>
        </div>
      </div>
    </div>
  );
}

export default FeedbackCard;
