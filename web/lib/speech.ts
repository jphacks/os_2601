export function unlockSpeech(): void {
  console.log("[speech] unlockSpeech（空実装。本物は T1-2）");
}

export async function speak(text: string): Promise<void> {
  console.log(`[speech] speak（空実装。本物は T1-2）: ${text}`);
}
