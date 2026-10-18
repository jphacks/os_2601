import { CHARACTERS, type CharacterId } from "./characters";

type Props = {
  value: CharacterId;
  onChange: (id: CharacterId) => void;
};

export function CharacterPicker({ value, onChange }: Props) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="mb-2 text-base font-bold text-slate-700">となりに座る人</legend>
      <div className="flex flex-wrap gap-2">
        {CHARACTERS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            onClick={() => onChange(id)}
            aria-pressed={value === id}
            className={`min-h-11 rounded-full px-4 text-base font-bold shadow-sm transition active:scale-95 ${
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
