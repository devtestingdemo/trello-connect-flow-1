
import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { Webhook, Play, Square, RotateCcw, Trash2 } from "lucide-react";
import { toast } from "@/hooks/use-toast";

interface WebhookManagementSectionProps {
  trelloBoards: any[];
  trelloConnected: boolean;
}

export const WebhookManagementSection: React.FC<WebhookManagementSectionProps> = ({
  trelloBoards,
  trelloConnected
}) => {
  const [selectedEvent, setSelectedEvent] = useState('');
  const [selectedBoard, setSelectedBoard] = useState('');
  const [selectedList, setSelectedList] = useState('');
  const [selectedLabel, setSelectedLabel] = useState('');
  const [inviteEmails, setInviteEmails] = useState('');
  const [webhooks, setWebhooks] = useState([
    { id: '1', event: 'Card moved', board: 'Project Management', status: 'active' },
    { id: '2', event: 'Card assigned', board: 'Development Sprint', status: 'paused' }
  ]);

  const eventTypes = [
    'Mentioned in a card',
    'Added to a card',
    'Card moved',
    'Card assigned',
    'Card due date changed',
    'Card completed',
    'Comment added',
    'Attachment added'
  ];

  const labels = ['High Priority', 'Bug', 'Feature', 'Documentation', 'Review'];

  const handleRegisterWebhook = () => {
    if (!selectedEvent || !selectedBoard) {
      toast({
        title: "Missing information",
        description: "Please select at least an event type and board",
        variant: "destructive"
      });
      return;
    }

    const newWebhook = {
      id: Date.now().toString(),
      event: selectedEvent,
      board: selectedBoard,
      status: 'active'
    };

    setWebhooks([...webhooks, newWebhook]);
    
    toast({
      title: "Webhook registered!",
      description: `Webhook for "${selectedEvent}" on "${selectedBoard}" has been created`,
    });

    // Reset form
    setSelectedEvent('');
    setSelectedBoard('');
    setSelectedList('');
    setSelectedLabel('');
  };

  const handleStopAllWebhooks = () => {
    setWebhooks(webhooks.map(w => ({ ...w, status: 'stopped' })));
    toast({
      title: "All webhooks stopped",
      description: "All active webhooks have been paused",
    });
  };

  const handleRerunAllWebhooks = () => {
    setWebhooks(webhooks.map(w => ({ ...w, status: 'active' })));
    toast({
      title: "All webhooks restarted",
      description: "All webhooks have been reactivated",
    });
  };

  if (!trelloConnected) {
    return (
      <div className="text-center py-8 text-gray-500">
        <Webhook className="w-12 h-12 mx-auto mb-3 opacity-50" />
        <p>Please connect your Trello account first to manage webhooks</p>
      </div>
    );
  }

  const selectedBoardData = trelloBoards.find(board => board.name === selectedBoard);

  return (
    <div className="space-y-6">
      {/* Webhook Creation Form */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Webhook className="w-5 h-5" />
            <span>Create New Webhook</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Event Type</Label>
              <Select value={selectedEvent} onValueChange={setSelectedEvent}>
                <SelectTrigger>
                  <SelectValue placeholder="Select event type" />
                </SelectTrigger>
                <SelectContent>
                  {eventTypes.map((event) => (
                    <SelectItem key={event} value={event}>
                      {event}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Target Board</Label>
              <Select value={selectedBoard} onValueChange={setSelectedBoard}>
                <SelectTrigger>
                  <SelectValue placeholder="Select board" />
                </SelectTrigger>
                <SelectContent>
                  {trelloBoards.map((board) => (
                    <SelectItem key={board.id} value={board.name}>
                      {board.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {selectedBoardData && (
              <div className="space-y-2">
                <Label>Target List (Optional)</Label>
                <Select value={selectedList} onValueChange={setSelectedList}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select list" />
                  </SelectTrigger>
                  <SelectContent>
                    {selectedBoardData.lists.map((list: string) => (
                      <SelectItem key={list} value={list}>
                        {list}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="space-y-2">
              <Label>Target Label (Optional)</Label>
              <Select value={selectedLabel} onValueChange={setSelectedLabel}>
                <SelectTrigger>
                  <SelectValue placeholder="Select label" />
                </SelectTrigger>
                <SelectContent>
                  {labels.map((label) => (
                    <SelectItem key={label} value={label}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Invite Members (Optional)</Label>
            <Textarea
              placeholder="email1@example.com, email2@example.com, @trellousername"
              value={inviteEmails}
              onChange={(e) => setInviteEmails(e.target.value)}
              className="min-h-[80px]"
            />
            <p className="text-xs text-gray-500">
              Comma separated list of emails or Trello usernames
            </p>
          </div>

          <Button onClick={handleRegisterWebhook} className="w-full">
            Register Webhook
          </Button>
        </CardContent>
      </Card>

      <Separator />

      {/* Webhook Management Controls */}
      <Card>
        <CardHeader>
          <CardTitle>Webhook Controls</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            <Button variant="destructive" onClick={handleStopAllWebhooks}>
              <Square className="w-4 h-4 mr-2" />
              Stop All Webhooks
            </Button>
            <Button variant="default" onClick={handleRerunAllWebhooks}>
              <Play className="w-4 h-4 mr-2" />
              Re-run All Webhooks
            </Button>
            <Button variant="outline">
              <RotateCcw className="w-4 h-4 mr-2" />
              Re-register All Webhooks
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Active Webhooks List */}
      <Card>
        <CardHeader>
          <CardTitle>Registered Webhooks</CardTitle>
        </CardHeader>
        <CardContent>
          {webhooks.length === 0 ? (
            <p className="text-gray-500 text-center py-4">No webhooks registered yet</p>
          ) : (
            <div className="space-y-3">
              {webhooks.map((webhook) => (
                <div key={webhook.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center space-x-3">
                    <Badge 
                      variant={webhook.status === 'active' ? 'default' : 'secondary'}
                      className={webhook.status === 'active' ? 'bg-green-500' : ''}
                    >
                      {webhook.status}
                    </Badge>
                    <div>
                      <p className="font-medium">{webhook.event}</p>
                      <p className="text-sm text-gray-500">{webhook.board}</p>
                    </div>
                  </div>
                  <Button variant="ghost" size="sm">
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
