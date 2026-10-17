export function startListening(onHeard: (text: string) => void): () => void {
  console.log("[voice] startListening（空実装。本物は T1-5）");
  return stopListening;
}

export function stopListening(): void {
  console.log("[voice] stopListening（空実装。本物は T1-5）");
}
