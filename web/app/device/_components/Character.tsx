import Image from "next/image";
import type { State } from "@/lib/api";
import character from "./character.png";

// 絵は 1 枚なので、状態は動きで表す。still は watching と同じにする（still を学習者に見せない。docs/06）
const MOTIONS: Record<State, string> = {
  created: "",
  watching: "",
  still: "",
  stuck: "-rotate-3",
  speaking: "animate-bounce",
  cooldown: "",
  checking: "-rotate-3",
  ended: "",
};

// となりのキャラクター。背景を透明にした絵（character.png）
export function Character({ state, className = "" }: { state: State; className?: string }) {
  return (
    <Image
      src={character}
      alt=""
      priority
      className={`origin-bottom object-contain object-bottom drop-shadow-xl transition-transform duration-500 ${MOTIONS[state]} ${className}`}
    />
  );
}
