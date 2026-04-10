import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { saveInterviewState, startSession, uploadResume } from "../lib/api";

function Upload() {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [candidateId, setCandidateId] = useState("");
  const [skills, setSkills] = useState([]);
  const [domainProfile, setDomainProfile] = useState({});
  const [selectedSkill, setSelectedSkill] = useState("");
  const [draftSkill, setDraftSkill] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState("");

  async function handleUpload(event) {
    event.preventDefault();
    if (!file) {
      setError("Choose a PDF resume before uploading.");
      return;
    }

    setIsUploading(true);
    setError("");

    try {
      const response = await uploadResume(file);
      setCandidateId(response.candidate_id);
      setSkills(response.skills || []);
      setDomainProfile(response.domain_profile || {});
      setSelectedSkill((response.skills || [])[0] || "");
    } catch (uploadError) {
      setError(uploadError.message);
    } finally {
      setIsUploading(false);
    }
  }

  function addSkill() {
    const nextSkill = draftSkill.trim();
    if (!nextSkill || skills.includes(nextSkill)) {
      return;
    }
    setSkills((current) => [...current, nextSkill]);
    setDomainProfile((current) => ({ ...current, [nextSkill]: "general" }));
    setSelectedSkill(nextSkill);
    setDraftSkill("");
  }

  function removeSkill(skill) {
    const nextSkills = skills.filter((item) => item !== skill);
    setSkills(nextSkills);
    setDomainProfile((current) => {
      const updated = { ...current };
      delete updated[skill];
      return updated;
    });
    if (selectedSkill === skill) {
      setSelectedSkill(nextSkills[0] || "");
    }
  }

  async function handleStart() {
    if (!candidateId || !selectedSkill) {
      setError("Upload a resume and confirm at least one skill first.");
      return;
    }

    setIsStarting(true);
    setError("");

    try {
      const response = await startSession({
        candidate_id: candidateId,
        skill: selectedSkill,
        sub_domain: domainProfile[selectedSkill] || "general"
      });

      const state = {
        candidateId,
        skill: selectedSkill,
        subDomain: domainProfile[selectedSkill] || "general",
        sessionId: response.session_id,
        question: response.question,
        difficulty: response.difficulty,
        round: response.round,
        elo: 1200
      };
      saveInterviewState(state);
      navigate(`/interview/${response.session_id}`, { state });
    } catch (startError) {
      setError(startError.message);
    } finally {
      setIsStarting(false);
    }
  }

  return (
    <div className="app-shell">
      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="glass-panel overflow-hidden">
          <div className="bg-halo p-8 sm:p-10">
            <p className="section-title">AI-Based Adaptive Mock Interview System</p>
            <h1 className="mt-4 max-w-2xl text-4xl font-bold leading-tight sm:text-5xl">
              Upload a resume, verify the extracted skills, and launch the first adaptive round.
            </h1>
            <p className="mt-4 max-w-xl text-base text-ink/70">
              This first screen is a trust-but-verify gate. We show what the parser extracted,
              let you edit it, and only then open a scored interview session.
            </p>
          </div>

          <form onSubmit={handleUpload} className="space-y-6 p-8 sm:p-10">
            <div>
              <label className="field-label" htmlFor="resume">
                Resume PDF
              </label>
              <input
                id="resume"
                type="file"
                accept="application/pdf"
                className="field-input cursor-pointer"
                onChange={(event) => setFile(event.target.files?.[0] || null)}
              />
            </div>

            <div className="flex flex-wrap gap-3">
              <button className="primary-button" disabled={isUploading} type="submit">
                {isUploading ? "Parsing resume..." : "Extract skills"}
              </button>
              <button
                className="secondary-button"
                disabled={isStarting || !skills.length}
                onClick={handleStart}
                type="button"
              >
                {isStarting ? "Starting session..." : "Start interview"}
              </button>
            </div>

            {error ? (
              <div className="rounded-2xl border border-ember/20 bg-ember/10 px-4 py-3 text-sm text-ember">
                {error}
              </div>
            ) : null}
          </form>
        </section>

        <aside className="glass-panel p-8 sm:p-10">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="section-title">Skill Confirmation</p>
              <h2 className="mt-3 text-3xl font-bold">Editable skill chips</h2>
            </div>
            <div className="rounded-full bg-ocean/10 px-4 py-2 text-sm font-semibold text-ocean">
              {skills.length} skills
            </div>
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            {skills.length ? (
              skills.map((skill) => (
                <div
                  key={skill}
                  className={`chip gap-3 pr-2 ${selectedSkill === skill ? "chip-active" : ""}`}
                >
                  <button onClick={() => setSelectedSkill(skill)} type="button">
                    {skill}
                  </button>
                  <button
                    aria-label={`Remove ${skill}`}
                    className="rounded-full bg-black/5 px-2 py-0.5 text-xs"
                    onClick={() => removeSkill(skill)}
                    type="button"
                  >
                    x
                  </button>
                </div>
              ))
            ) : (
              <p className="text-sm text-ink/60">
                Extracted skills will appear here after a successful upload.
              </p>
            )}
          </div>

          <div className="mt-6 flex gap-3">
            <input
              className="field-input"
              placeholder="Add a missing skill"
              value={draftSkill}
              onChange={(event) => setDraftSkill(event.target.value)}
            />
            <button className="secondary-button" onClick={addSkill} type="button">
              Add
            </button>
          </div>

          <div className="mt-8 rounded-[24px] bg-ink p-6 text-white">
            <p className="text-sm uppercase tracking-[0.2em] text-white/70">Selected lane</p>
            <h3 className="mt-3 text-2xl font-bold">{selectedSkill || "Pick a skill"}</h3>
            <p className="mt-2 text-sm text-white/75">
              Sub-domain: {selectedSkill ? domainProfile[selectedSkill] || "general" : "--"}
            </p>
            <p className="mt-6 text-sm text-white/70">
              Start with the strongest verified skill first, then repeat sessions later for
              weaker areas. The dashboard will preserve Elo progression per skill.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}

export default Upload;
