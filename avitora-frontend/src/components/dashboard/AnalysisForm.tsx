'use client';

import { useState } from 'react';
import type { AnalysisFormValue } from '@/types/api';
import { Button } from '@/components/ui/Button';

interface AnalysisFormProps {
  onSubmit: (data: AnalysisFormValue) => Promise<void>;
}

export function AnalysisForm({ onSubmit }: AnalysisFormProps) {
  const [pasteText, setPasteText] = useState('');
  const [sportHint, setSportHint] = useState<'soccer' | 'mlb' | 'npb' | 'nba' | 'mixed'>('mixed');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!pasteText.trim()) {
      setError('分析対象のテキストを入力してください');
      return;
    }

    setIsLoading(true);
    try {
      await onSubmit({ paste_text: pasteText, sport_hint: sportHint });
      setPasteText('');
    } catch (err: any) {
      setError(err?.response?.data?.detail || '分析に失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-gap-md">
      <div>
        <label htmlFor="pasteText" className="block text-sm font-medium text-gray-900 mb-gap-xs">
          ペースト対象
        </label>
        <textarea
          id="pasteText"
          value={pasteText}
          onChange={(e) => setPasteText(e.target.value)}
          className="w-full px-gap-md py-gap-sm rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent min-h-[120px]"
          placeholder="分析対象のテキストを貼り付けてください"
        />
      </div>

      <div>
        <label htmlFor="sportHint" className="block text-sm font-medium text-gray-900 mb-gap-xs">
          スポーツヒント
        </label>
        <select
          id="sportHint"
          value={sportHint}
          onChange={(e) => setSportHint(e.target.value as any)}
          className="w-full px-gap-md py-gap-sm rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
        >
          <option value="mixed">混合</option>
          <option value="soccer">サッカー</option>
          <option value="mlb">MLB</option>
          <option value="npb">NPB</option>
          <option value="nba">NBA</option>
        </select>
      </div>

      {error && (
        <div className="rounded-lg bg-danger-600 bg-opacity-10 p-gap-md">
          <p className="text-sm text-danger-600">{error}</p>
        </div>
      )}

      <Button type="submit" isLoading={isLoading} className="w-full focus:outline-none focus:ring-2 focus:ring-primary-500">
        分析開始
      </Button>
    </form>
  );
}
