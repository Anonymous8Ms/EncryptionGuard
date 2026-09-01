import { useState } from 'react';
import clsx from 'clsx';
import { submitFeedback } from '../services/api';

interface FeedbackButtonsProps {
  caseId: string;
  onFeedbackSubmitted?: () => void;
}

export default function FeedbackButtons({ caseId, onFeedbackSubmitted }: FeedbackButtonsProps) {
  const [submitting, setSubmitting] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFeedback = async (feedback: 'confirm_abuse' | 'legitimate' | 'need_more_evidence') => {
    setSubmitting(feedback);
    setError(null);
    try {
      await submitFeedback({ case_id: caseId, feedback });
      setSubmitted(feedback);
      onFeedbackSubmitted?.();
    } catch (err) {
      setError('Failed to submit feedback. Please try again.');
      console.error('Feedback submission error:', err);
    } finally {
      setSubmitting(null);
    }
  };

  if (submitted) {
    return (
      <div className="border border-border bg-cream p-8">
        <div className="flex items-center gap-4 mb-4">
          <div className="w-8 h-8 bg-cobalt" />
          <div>
            <p className="text-xl font-bold text-jet">Decision Recorded</p>
            <p className="mono-label">{submitted.replace(/_/g, ' ').toUpperCase()}</p>
          </div>
        </div>
        <p className="text-deep">
          Your analysis has been recorded and will be used to improve model accuracy.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="grid grid-cols-3 gap-px bg-border border border-border">
        {/* Confirm Abuse */}
        <button
          onClick={() => handleFeedback('confirm_abuse')}
          disabled={submitting !== null}
          className={clsx(
            'bg-cream p-8 text-left transition-colors',
            'hover:bg-jet hover:text-cream group',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          <p className="mono-label mb-4 group-hover:text-cream/60">01</p>
          <p className="text-2xl font-bold mb-3">Confirm Abuse</p>
          <p className="text-sm text-deep group-hover:text-cream/80">
            Mark as coordinated refund abuse ring
          </p>
        </button>

        {/* Legitimate */}
        <button
          onClick={() => handleFeedback('legitimate')}
          disabled={submitting !== null}
          className={clsx(
            'bg-cream p-8 text-left transition-colors',
            'hover:bg-cobalt hover:text-cream group',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          <p className="mono-label mb-4 group-hover:text-cream/60">02</p>
          <p className="text-2xl font-bold mb-3">Legitimate</p>
          <p className="text-sm text-deep group-hover:text-cream/80">
            False positive — legitimate activity
          </p>
        </button>

        {/* Escalate */}
        <button
          onClick={() => handleFeedback('need_more_evidence')}
          disabled={submitting !== null}
          className={clsx(
            'bg-cream p-8 text-left transition-colors',
            'hover:bg-deep hover:text-cream group',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          <p className="mono-label mb-4 group-hover:text-cream/60">03</p>
          <p className="text-2xl font-bold mb-3">Escalate</p>
          <p className="text-sm text-deep group-hover:text-cream/80">
            Require additional investigation
          </p>
        </button>
      </div>

      {error && (
        <div className="mt-px border border-border bg-red-50 px-6 py-4">
          <p className="mono-label text-red-600">{error}</p>
        </div>
      )}
    </div>
  );
}
