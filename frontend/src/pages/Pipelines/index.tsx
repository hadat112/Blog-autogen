import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import {
  createPipeline,
  deletePipeline,
  getPipelines,
  updatePipeline,
} from "../../api/client";
import { Pipeline } from "../../api/types";
import { Button } from "../../components/ui/Button";
import PipelineCard from "./components/PipelineCard";
import PipelineForm from "./components/PipelineForm";
import PipelinesSkeleton from "./components/PipelinesSkeleton";

const Pipelines = () => {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editingPipeline, setEditingPipeline] = useState<Pipeline | null>(null);

  const { data: pipelines = [], isLoading } = useQuery({
    queryKey: ["pipelines"],
    queryFn: async () => {
      const { data } = await getPipelines();
      return data;
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deletePipeline,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipelines"] });
    },
    onError: () => {
      alert("Failed to delete pipeline");
    },
  });

  const saveMutation = useMutation({
    mutationFn: (formData: Partial<Pipeline>) => {
      if (editingPipeline) {
        return updatePipeline(editingPipeline.id, formData);
      } else {
        return createPipeline(formData);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipelines"] });
      setShowForm(false);
      setEditingPipeline(null);
    },
    onError: (error: any) => {
      alert(
        "Failed to save pipeline: " +
          (error.response?.data?.detail || error.message),
      );
    },
  });

  const handleDelete = (id: string) => {
    if (window.confirm("Are you sure you want to delete this pipeline?")) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-xl font-bold text-content-primary">
          Process Pipelines
        </h3>
        <Button
          onClick={() => {
            setEditingPipeline(null);
            setShowForm(true);
          }}
          className="flex items-center space-x-2"
        >
          <Plus size={18} />
          <span>New Pipeline</span>
        </Button>
      </div>

      {isLoading ? (
        <PipelinesSkeleton />
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {pipelines.length === 0 ? (
            <div className="py-20 text-center bg-surface rounded-xl border border-dashed border-border-strong">
              <p className="text-content-secondary">
                No pipelines defined. Create one to start processing stories.
              </p>
            </div>
          ) : (
            pipelines.map((p) => (
              <PipelineCard
                key={p.id}
                pipeline={p}
                onEdit={(pipeline) => {
                  setEditingPipeline(pipeline);
                  setShowForm(true);
                }}
                onDelete={handleDelete}
              />
            ))
          )}
        </div>
      )}

      {showForm && (
        <PipelineForm
          pipeline={editingPipeline}
          onClose={() => {
            setShowForm(false);
            setEditingPipeline(null);
          }}
          onSave={(data) => saveMutation.mutate(data)}
        />
      )}
    </div>
  );
};

export default Pipelines;
