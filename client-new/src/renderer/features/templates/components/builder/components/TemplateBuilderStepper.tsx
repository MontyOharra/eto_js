/**
 * TemplateBuilderStepper
 * Progress indicator showing current step in template building process
 */

type BuilderStep = 'signature-objects' | 'extraction-fields' | 'pipeline';

interface StepConfig {
  id: BuilderStep;
  number: number;
  label: string;
}

const STEPS: StepConfig[] = [
  { id: 'signature-objects', number: 1, label: 'Signature Objects' },
  { id: 'extraction-fields', number: 2, label: 'Extraction Fields' },
  { id: 'pipeline', number: 3, label: 'Pipeline' },
];

interface TemplateBuilderStepperProps {
  currentStep: BuilderStep;
  completedSteps: Set<BuilderStep>;
}

export function TemplateBuilderStepper({
  currentStep,
  completedSteps,
}: TemplateBuilderStepperProps) {
  const currentStepNumber = STEPS.find((s) => s.id === currentStep)?.number || 1;

  return (
    <div className="flex items-center space-x-3">
      {STEPS.map((step, index) => {
        const isActive = step.id === currentStep;
        const isCompleted = completedSteps.has(step.id);
        const isPast = step.number < currentStepNumber;

        return (
          <div key={step.id} className="flex items-center">
            {/* Step Circle */}
            <div className="flex items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : isCompleted || isPast
                    ? 'bg-green-600 text-white'
                    : 'bg-gray-700 text-gray-400'
                }`}
              >
                {isCompleted || isPast ? (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                ) : (
                  step.number
                )}
              </div>
              <span
                className={`ml-2 text-sm font-medium ${
                  isActive ? 'text-white' : 'text-gray-400'
                }`}
              >
                {step.label}
              </span>
            </div>

            {/* Divider */}
            {index < STEPS.length - 1 && (
              <div className="w-12 h-0.5 bg-gray-700 mx-3"></div>
            )}
          </div>
        );
      })}
    </div>
  );
}
