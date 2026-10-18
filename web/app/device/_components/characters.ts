import type { StaticImageData } from "next/image";
import handsome from "./character.png";
import teacher from "./teacher.png";

export type CharacterId = "handsome" | "teacher";

type CharacterInfo = { id: CharacterId; label: string; image: StaticImageData };

export const CHARACTERS: CharacterInfo[] = [
  { id: "handsome", label: "イケメン", image: handsome },
  { id: "teacher", label: "先生", image: teacher },
];

export const DEFAULT_CHARACTER: CharacterId = "handsome";

export function characterOf(id: CharacterId): CharacterInfo {
  return CHARACTERS.find((c) => c.id === id) ?? CHARACTERS[0];
}
