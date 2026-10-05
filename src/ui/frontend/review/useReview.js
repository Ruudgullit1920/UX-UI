import { useEffect, useRef, useState } from "react";
import { getReview, saveRevision, transitionRevision } from "../api/reviews.js";
import { getAudit } from "../api/audits.js";
import { publishRevision } from "../api/publications.js";
import { cleanChanges, validateChanges } from "./reviewModel.js";

export const actionTitles = { load: "Couldn’t load review", save: "Couldn’t save your changes", validate: "Couldn’t validate this revision", approve: "Couldn’t approve this revision", publish: "Couldn’t publish the reviewed report", refresh: "Couldn’t refresh the revision" };
export default function useReview(api, job, onDirty, onJob) {
  const alive = useRef(true);
  useEffect(() => () => { alive.current = false; }, []);
  const [review, setReview] = useState(null);
  const [changes, setChanges] = useState({});
  const [baseline, setBaseline] = useState({});
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState("");
  const [failure, setFailure] = useState(null);
  const [validation, setValidation] = useState("");
  const [notice, setNotice] = useState("");
  const [conflict, setConflict] = useState(false);
  const [fresh, setFresh] = useState(false);
  const [publication, setPublication] = useState(null);
  const [retry, setRetry] = useState(0);
  const revisionId = review?.currentRevision || null;
  const current = review?.revisions?.find(item => item.revisionId === revisionId);
  const dirty = JSON.stringify(cleanChanges(changes)) !== JSON.stringify(cleanChanges(baseline)) || !!reason.trim();
  useEffect(() => { onDirty(dirty); }, [dirty, onDirty]);
  useEffect(() => {
    let live = true;
    setFailure(null);
    getReview(api, job.id).then(data => {
      if (!live) return;
      setReview(data);
      const saved = data.revisions?.find(item => item.revisionId === data.currentRevision)?.changes || {};
      setChanges(saved); setBaseline(saved);
    }).catch(error => { if (live) setFailure({ action: "load", error }); });
    return () => { live = false; };
  }, [api, job.id, retry]);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(""), 6000);
    return () => clearTimeout(timer);
  }, [notice]);
  function edit(id, fields) {
    setChanges(old => ({ ...old, [id]: fields }));
    setValidation(""); setNotice("");
    // A changed draft supersedes a failed action against the previous state.
    setFailure(null);
  }
  async function refreshConflict() {
    setBusy("refresh");
    try { setReview(await getReview(api, job.id)); setFresh(true); setFailure(null); }
    catch (error) { setFailure({ action: "refresh", error }); } finally { setBusy(""); }
  }
  function resolveConflict(keep) {
    const latest = current?.changes || {};
    setBaseline(latest);
    if (!keep) { setChanges(latest); setReason(""); }
    setConflict(false); setFresh(false); setFailure(null);
    setNotice(keep ? "Your draft is retained. Compare it with the current revision before saving." : "The latest revision is loaded.");
  }
  async function action(name) {
    if (busy || conflict || !review) return;
    if (name !== "save" && dirty) return;
    const cleaned = cleanChanges(changes);
    if (name === "save") {
      const message = validateChanges(cleaned); setValidation(message);
      if (message) return;
    }
    setBusy(name); setFailure(null); setNotice("");
    let appliedRevisionId = revisionId;
    try {
      if (name === "publish") {
        const result = await publishRevision(api, job.id, revisionId);
        setPublication(result.publication);
        setNotice("Reviewed report published.");
      } else {
        const result = name === "save" ? await saveRevision(api, job.id, cleaned, revisionId, reason) : await transitionRevision(api, job.id, name, revisionId);
        appliedRevisionId = result.revisionId;
        // Mutation response is authoritative. A failed follow-up read must never turn success into a failed mutation.
        setReview(old => ({ ...old, currentRevision: result.revisionId, reviewStatus: result.reviewStatus, revisions: [...old.revisions.filter(item => item.revisionId !== result.revisionId), result] }));
        setChanges(result.changes || {}); setBaseline(result.changes || {}); setReason("");
        setNotice(name === "save" ? "Revision saved." : name === "validate" ? "Revision validated." : "Revision approved.");
      }
      setFailure(null);
      try {
        const refreshed = await getReview(api, job.id);
        setReview(refreshed);
        if (refreshed.currentRevision !== appliedRevisionId) { setConflict(true); setFresh(true); setNotice(""); }
        if (name === "publish" && onJob) {
          const updatedJob = await getAudit(api, job.id);
          if (alive.current) onJob(updatedJob);
        }
      }
      catch (error) { setFailure({ action: "refresh", error, afterSuccess: true }); }
    } catch (error) {
      setFailure({ action: name, error });
      if (error.status === 409) { setConflict(true); setFresh(false); }
    } finally { setBusy(""); }
  }
  return { review, changes, reason, setReason: value => { setReason(value); setFailure(null); setNotice(""); }, busy, failure, dismiss: () => setFailure(null), validation, notice, conflict, fresh, publication, revisionId, current, dirty, edit, action, refreshConflict, resolveConflict, retry: () => setRetry(x => x + 1) };
}
