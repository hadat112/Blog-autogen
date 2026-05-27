import React from 'react';
import { Card } from '../../../components/ui/Card';
import { Skeleton } from '../../../components/ui/Skeleton';

const PipelinesSkeleton = () => {
  return (
    <div className="grid grid-cols-1 gap-4">
      {[1, 2, 3].map((i) => (
        <Card key={i} className="p-6 flex items-center justify-between h-24">
          <div className="flex items-center space-x-4 w-full">
            <Skeleton className="rounded-lg w-12 h-12" />
            <div className="space-y-2 w-1/2">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
};

export default PipelinesSkeleton;
