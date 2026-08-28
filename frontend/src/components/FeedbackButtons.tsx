import { useState } from 'react';
import { ShieldCheck, ThumbsUp, HelpCircle } from 'lucide-react';
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
      <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg">
        <ShieldCheck className="h-5 w-5 text-green-600" />
        <span className="text-green-700 text-sm font-medium">
          Feedback submitted: {submitted.replace(/_/g, ' ')}
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-gray-700 mb-2">Analyst Feedback</p>
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => handleFeedback('confirm_abuse')}
          disabled={submitting !== null}
          className={clsx(
            'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
            'bg-red-100 text-red-700 hover:bg-red-200 border border-red-300',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          <ShieldCheck className="h-4 w-4" />
          {submitting === 'confirm_abuse' ? 'Submitting...' : 'Confirm Abuse'}
        </button>
        <button
          onClick={() => handleFeedback('legitimate')}
          disabled={submitting !== null}
          className={clsx(
            'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
            'bg-green-100 text-green-700 hover:bg-green-200 border border-green-300',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          <ThumbsUp className="h-4 w-4" />
          {submitting === 'legitimate' ? 'Submitting...' : 'Legitimate'}
        </button>
        <button
          onClick={() => handleFeedback('need_more_evidence')}
          disabled={submitting !== null}
          className={clsx(
            'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
            'bg-yellow-100 text-yellow-700 hover:bg-yellow-200 border border-yellow-300',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          <HelpCircle className="h-4 w-4" />
          {submitting === 'need_more_evidence' ? 'Submitting...' : 'Need More Evidence'}
        </button>
      </div>
      {error && (
        <p className="text-sm text-red-600 mt-1">{error}</p>
      )}
    </div>
  );
}
