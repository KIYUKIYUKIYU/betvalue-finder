'use client';

import { useState, useEffect } from 'react';
import type { Rakeback } from '@/types/api';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

interface RakebackSettingsProps {
  initialData: Rakeback;
  onSave: (data: Rakeback) => Promise<void>;
}

export function RakebackSettings({ initialData, onSave }: RakebackSettingsProps) {
  const [defaultRate, setDefaultRate] = useState(initialData.default.toString());
  const [mlbRate, setMlbRate] = useState(initialData.mlb.toString());
  const [npbRate, setNpbRate] = useState(initialData.npb.toString());
  const [soccerRate, setSoccerRate] = useState(initialData.soccer.toString());
  const [nbaRate, setNbaRate] = useState(initialData.nba.toString());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    setDefaultRate(initialData.default.toString());
    setMlbRate(initialData.mlb.toString());
    setNpbRate(initialData.npb.toString());
    setSoccerRate(initialData.soccer.toString());
    setNbaRate(initialData.nba.toString());
  }, [initialData]);

  const validateRakeback = (value: string): boolean => {
    const num = parseFloat(value);
    return !isNaN(num) && num >= 0 && num <= 3;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess(false);

    const fields = [
      { name: 'デフォルト', value: defaultRate },
      { name: 'MLB', value: mlbRate },
      { name: 'NPB', value: npbRate },
      { name: 'サッカー', value: soccerRate },
      { name: 'NBA', value: nbaRate },
    ];

    for (const field of fields) {
      if (!validateRakeback(field.value)) {
        setError(`${field.name}のレーキバックは0〜3%の範囲で入力してください`);
        return;
      }
    }

    setIsLoading(true);
    try {
      await onSave({
        default: parseFloat(defaultRate),
        mlb: parseFloat(mlbRate),
        npb: parseFloat(npbRate),
        soccer: parseFloat(soccerRate),
        nba: parseFloat(nbaRate),
      });
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      setError(err?.response?.data?.detail || '保存に失敗しました');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-gap-md">
      <Input
        label="デフォルト レーキバック (%)"
        type="number"
        step="0.1"
        min="0"
        max="3"
        value={defaultRate}
        onChange={(e) => setDefaultRate(e.target.value)}
        hint="0〜3%の範囲で入力してください"
      />

      <Input
        label="MLB レーキバック (%)"
        type="number"
        step="0.1"
        min="0"
        max="3"
        value={mlbRate}
        onChange={(e) => setMlbRate(e.target.value)}
        hint="0〜3%の範囲で入力してください"
      />

      <Input
        label="NPB レーキバック (%)"
        type="number"
        step="0.1"
        min="0"
        max="3"
        value={npbRate}
        onChange={(e) => setNpbRate(e.target.value)}
        hint="0〜3%の範囲で入力してください"
      />

      <Input
        label="サッカー レーキバック (%)"
        type="number"
        step="0.1"
        min="0"
        max="3"
        value={soccerRate}
        onChange={(e) => setSoccerRate(e.target.value)}
        hint="0〜3%の範囲で入力してください"
      />

      <Input
        label="NBA レーキバック (%)"
        type="number"
        step="0.1"
        min="0"
        max="3"
        value={nbaRate}
        onChange={(e) => setNbaRate(e.target.value)}
        hint="0〜3%の範囲で入力してください"
      />

      {error && (
        <div className="rounded-lg bg-danger-600 bg-opacity-10 p-gap-md">
          <p className="text-sm text-danger-600">{error}</p>
        </div>
      )}

      {success && (
        <div className="rounded-lg bg-success-600 bg-opacity-10 p-gap-md">
          <p className="text-sm text-success-600">設定を保存しました</p>
        </div>
      )}

      <Button type="submit" isLoading={isLoading}>
        保存
      </Button>
    </form>
  );
}
