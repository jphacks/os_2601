import type { StaticImageData } from "next/image";
import normal from "./character.png";
import joy from "./character-joy.png";
import anger from "./character-anger.png";
import sad from "./character-sad.png";
import fun from "./character-fun.png";
import teacher from "./teacher.png";
import friend from "./friend.png";

export type CharacterId = "handsome" | "teacher" | "friend";
// normal：ふだん / joy：喜 / anger：怒 / sad：哀 / fun：楽
export type Mood = "normal" | "joy" | "anger" | "sad" | "fun";

type CharacterInfo = { id: CharacterId; label: string; images: Record<Mood, StaticImageData> };

const HANDSOME = { normal, joy, anger, sad, fun };

// 先生・友達は絵が 1 枚ずつなので、どの表情でも同じ絵を出す。表情の絵が届いたら images を差し替える
const same = (image: StaticImageData): Record<Mood, StaticImageData> => ({
  normal: image,
  joy: image,
  anger: image,
  sad: image,
  fun: image,
});

export const CHARACTERS: CharacterInfo[] = [
  { id: "handsome", label: "イケメン", images: HANDSOME },
  { id: "teacher", label: "先生", images: same(teacher) },
  { id: "friend", label: "友達", images: same(friend) },
];

export const DEFAULT_CHARACTER: CharacterId = "handsome";

export function characterOf(id: CharacterId): CharacterInfo {
  return CHARACTERS.find((c) => c.id === id) ?? CHARACTERS[0];
}
