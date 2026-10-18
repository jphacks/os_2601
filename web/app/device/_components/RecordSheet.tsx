import type { SessionDetail } from "@/lib/api";
import { SessionRecord } from "@/app/_components/record/SessionRecord";

type Props = {
  session: SessionDetail;
  onClose: () => void;
};

export function RecordSheet({ session, onClose }: Props) {
  return (
    <div role="dialog" aria-modal="true" aria-label="今日の記録" className="fixed inset-0 z-20 flex flex-col bg-white text-gray-900">
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
        <h1 className="text-lg font-bold">今日の記録</h1>
        <button type="button" onClick={onClose} className="rounded-full bg-gray-100 px-5 py-2.5 font-bold">
          とじる
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-3xl p-4">
          <SessionRecord session={session} />
        </div>
      </div>
    </div>
  );
}
