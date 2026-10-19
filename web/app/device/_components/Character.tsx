import Image from "next/image";
import type { State } from "@/lib/api";
import { characterOf, type CharacterId } from "@/app/_components/characters/characters";

// 絵は 1 枚なので、状態は動きで表す。still は watching と同じにする（still を学習者に見せない。docs/06）
const MOTIONS: Record<State, string> = {
  created: "",
  watching: "",
  still: "",
  stuck: "-rotate-3",
  speaking: "motion-safe:animate-bounce",
  cooldown: "",
  checking: "-rotate-3",
  ended: "",
};

// となりのキャラクター。背景を透明にした絵（characters.ts の一覧から選ぶ）
export function Character({ state, id, className = "" }: { state: State; id: CharacterId; className?: string }) {
  return (
    <Image
      src={characterOf(id).image}
      alt=""
      priority
      className={`origin-bottom object-contain object-bottom drop-shadow-xl motion-safe:transition-transform motion-safe:duration-500 ${MOTIONS[state]} ${className}`}
    />
  );
}
