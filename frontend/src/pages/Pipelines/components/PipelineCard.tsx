import React from 'react';
import { GitBranch, Edit2, Trash2 } from 'lucide-react';
import { Pipeline } from '../../../api/types';
import { Card, CardHeader, CardTitle, CardContent } from '../../../components/ui/Card';
import { Button } from '../../../components/ui/Button';

interface PipelineCardProps {
  pipeline: Pipeline;
  onEdit: (pipeline: Pipeline) => void;
  onDelete: (id: string) => void;
}

const PipelineCard: React.FC<PipelineCardProps> = ({ pipeline, onEdit, onDelete }) => {
  return (
    <Card className="flex flex-row items-center justify-between p-6 hover:shadow-md transition-shadow">
      <div className="flex items-center space-x-4">
        <div className="p-3 bg-accent/10 text-accent rounded-lg">
          <GitBranch size={24} />
        </div>
        <div>
          <h4 className="font-bold text-content-primary">{pipeline.name}</h4>
          <div className="flex items-center space-x-3 mt-1">
            <span className="text-xs font-semibold text-content-secondary bg-surface-subtle px-2 py-0.5 rounded uppercase">
              {pipeline.language}
            </span>
            <span className="text-xs text-content-tertiary">
              Steps: {Object.values(pipeline.step_accounts).filter(v => v).length} configured
            </span>
            {pipeline.settings?.wp_category_id && (
              <span className="text-xs text-content-tertiary">
                WP category: {pipeline.settings.wp_category_id}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center space-x-2">
        <Button 
          variant="ghost"
          size="icon"
          onClick={() => onEdit(pipeline)}
          className="text-content-tertiary hover:text-status-warning"
        >
          <Edit2 size={18} />
        </Button>
        <Button 
          variant="ghost"
          size="icon"
          onClick={() => onDelete(pipeline.id)}
          className="text-content-tertiary hover:text-status-danger"
        >
          <Trash2 size={18} />
        </Button>
      </div>
    </Card>
  );
};

export default PipelineCard;
