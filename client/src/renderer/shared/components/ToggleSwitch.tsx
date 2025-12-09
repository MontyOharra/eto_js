/**
 * ToggleSwitch
 * A reusable slider toggle component for boolean settings
 */

interface ToggleSwitchProps {
  id: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  description?: string;
  disabled?: boolean;
  size?: 'sm' | 'md';
}

export function ToggleSwitch({
  id,
  checked,
  onChange,
  label,
  description,
  disabled = false,
  size = 'md',
}: ToggleSwitchProps) {
  const sizeClasses = {
    sm: {
      track: 'w-8 h-4',
      thumb: 'w-3 h-3',
      translateOn: 'translate-x-4',
      translateOff: 'translate-x-0.5',
    },
    md: {
      track: 'w-10 h-5',
      thumb: 'w-4 h-4',
      translateOn: 'translate-x-5',
      translateOff: 'translate-x-0.5',
    },
  };

  const sizes = sizeClasses[size];

  return (
    <div className="flex items-start">
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        className={`
          ${sizes.track}
          relative inline-flex flex-shrink-0
          rounded-full border-2 border-transparent
          transition-colors duration-200 ease-in-out
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900
          ${disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}
          ${checked ? 'bg-blue-600' : 'bg-gray-600'}
        `}
      >
        <span
          className={`
            ${sizes.thumb}
            pointer-events-none inline-block
            rounded-full bg-white shadow-lg
            transform transition-transform duration-200 ease-in-out
            ${checked ? sizes.translateOn : sizes.translateOff}
          `}
        />
      </button>
      <div className="ml-3 flex flex-col">
        <label
          htmlFor={id}
          className={`text-xs font-medium ${disabled ? 'text-gray-500' : 'text-gray-300'} cursor-pointer`}
          onClick={() => !disabled && onChange(!checked)}
        >
          {label}
        </label>
        {description && (
          <span className="text-xs text-gray-500 mt-0.5">{description}</span>
        )}
      </div>
    </div>
  );
}
