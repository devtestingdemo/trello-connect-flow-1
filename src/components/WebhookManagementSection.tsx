
import React, { useState, useEffect } from 'react';
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
  apiKey: string;
  token: string;
}

export const WebhookManagementSection: React.FC<WebhookManagementSectionProps> = ({
  trelloBoards,
  trelloConnected,
  apiKey,
  token
}) => {
  const [selectedEvent, setSelectedEvent] = useState('');
  const [selectedBoard, setSelectedBoard] = useState('');
  const [selectedList, setSelectedList] = useState('');
  const [selectedLabel, setSelectedLabel] = useState('');
  const [inviteEmails, setInviteEmails] = useState('');
  const [webhooks, setWebhooks] = useState([]);

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

  const handleRegisterWebhook = async () => {
    if (!selectedEvent || !selectedBoard) {
      toast({
        title: "Missing information",
        description: "Please select at least an event type and board",
        variant: "destructive"
      });
      return;
    }
    if (!apiKey || !token) {
      toast({
        title: "Missing Trello credentials",
        description: "Please connect Trello and provide API Key & Token.",
        variant: "destructive"
      });
      return;
    }
    try {
      // Find the board id
      const boardObj = trelloBoards.find(b => b.name === selectedBoard);
      if (!boardObj) throw new Error("Board not found");
      // Trello webhook API: https://developer.atlassian.com/cloud/trello/guides/webhooks/
      // You must provide a callbackURL that Trello can reach (publicly accessible)
      //w.location.origin + "/api/trello-webhook-callback";
      // Us For demo, we'll use a placeholder. In production, replace with your backend endpoint.
      const callbackURL = "https://hook.eu2.make.com/lz2x1x7y29933vbj03kaq6cwwcqq4u2d";  
      console.log("apiKey, token, boardObj");
      
      console.log(apiKey, token, boardObj);
      console.log(callbackURL);
      console.log(boardObj.id);
      console.log(selectedEvent);
      console.log(selectedBoard);
      //windoe Trello's /1/tokens/{token}/webhooks/ endpoint as in the curl example
      const response = await fetch(`https://api.trello.com/1/tokens/${token}/webhooks/`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            key: apiKey,
            callbackURL,
            idModel: boardObj.id,
            description: `Webhook for ${selectedEvent} on ${selectedBoard}`
          })
        }
      );
      console.log(response);
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.message || 'Failed to register webhook');
      }
      const webhookData = await response.json();
      console.log(webhookData);
      const newWebhook = {
        id: webhookData.id,
        event: selectedEvent,
        board: selectedBoard,
        status: 'active'
      };
      setWebhooks([...webhooks, newWebhook]);
      toast({
        title: "Webhook registered!",
        description: `Webhook for \"${selectedEvent}\" on \"${selectedBoard}\" has been created`,
      });
      // Reset form
      setSelectedEvent('');
      setSelectedBoard('');
      setSelectedList('');
      setSelectedLabel('');
    } catch (err: any) {
      console.log(err);
      toast({
        title: "Webhook registration failed",
        description: err.message || 'Could not register webhook with Trello.',
        variant: "destructive"
      });
    }
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

  const fetchWebhooks = async () => {
    if (!apiKey || !token) {
      toast({
        title: "Missing Trello credentials",
        description: "Please connect Trello and provide API Key & Token.",
        variant: "destructive"
      });
      return;
    }
    try {
      const response = await fetch(`https://api.trello.com/1/tokens/${token}/webhooks?key=${apiKey}`);
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.message || 'Failed to fetch webhooks');
      }
      const data = await response.json();
      setWebhooks(data.map((wh: any) => ({
        id: wh.id,
        event: wh.description, // Trello doesn't store your custom event, so use description
        board: trelloBoards.find(b => b.id === wh.idModel)?.name || wh.idModel,     // You may want to resolve this to a board name
        status: wh.active ? 'active' : 'inactive'
      })));
    } catch (err: any) {
      toast({
        title: "Failed to fetch webhooks",
        description: err.message || 'Could not fetch webhooks from Trello.',
        variant: "destructive"
      });
    }
  };

  useEffect(() => {
    if (apiKey && token) {
      fetchWebhooks();
    }
    // eslint-disable-next-line
  }, [apiKey, token]);

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
            <Button onClick={fetchWebhooks} variant="outline">
              Refresh Webhooks
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
