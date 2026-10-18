import { CHARACTERS, type CharacterId } from "@/app/_components/characters/characters";

type Props = {
  value: CharacterId;
  onChange: (id: CharacterId) => void;
  disabled?: boolean;
};

export function CharacterPicker({ value, onChange, disabled = false }: Props) {
  return (
    <fieldset disabled={disabled} className="flex flex-col gap-2 disabled:opacity-50">
      <legend className="mb-1 text-sm font-bold text-slate-700">となりに座る人</legend>
      <div className="flex flex-wrap gap-2">
        {CHARACTERS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            disabled={disabled}
            onClick={() => onChange(id)}
            aria-pressed={value === id}
            className={`min-h-10 rounded-full px-3 text-sm font-bold shadow-sm transition active:scale-95 ${
              value === id ? "bg-sky-500 text-white" : "bg-white text-slate-600"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
    </fieldset>
  );
}
