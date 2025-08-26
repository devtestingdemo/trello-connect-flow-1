
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

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';
const TRELLO_WEBHOOK_CALLBACK_URL = `${API_BASE_URL}/trello-webhook`;

interface WebhookManagementSectionProps {
  trelloBoards: any[];
  trelloConnected: boolean;
  userEmail: string;
}

export const WebhookManagementSection: React.FC<WebhookManagementSectionProps> = ({
  trelloBoards,
  trelloConnected,
  userEmail
}) => {
  const [selectedEvent, setSelectedEvent] = useState('');
  const [selectedBoard, setSelectedBoard] = useState('');
  const [selectedList, setSelectedList] = useState('');
  const [selectedLabel, setSelectedLabel] = useState('');
  const [inviteEmails, setInviteEmails] = useState('');
  const [webhooks, setWebhooks] = useState([]);

  const eventTypes = [
    'Mentioned in a card',
    'Added to a card'
  ];

  const labels = ['High Priority', 'Bug', 'Feature', 'Documentation', 'Review'];
  
  const handleRegisterWebhook = async () => {
    if (!selectedEvent) {
      toast({
        title: "Missing information",
        description: "Please select at least an event type.",
        variant: "destructive"
      });
      return;
    }
    if (!userEmail) {
      toast({
        title: "Missing user email",
        description: "Please log in to register webhooks.",
        variant: "destructive"
      });
      return;
    }
    // Determine boards to register webhook for
    let boardsToRegister: any[] = [];
    if (!selectedBoard || selectedBoard === '__ALL__') {
      boardsToRegister = trelloBoards;
    } else {
      const boardObj = trelloBoards.find(b => b.name === selectedBoard);
      if (!boardObj) {
        toast({
          title: "Board not found",
          description: `Could not find board: ${selectedBoard}`,
          variant: "destructive"
        });
        return;
      }
      boardsToRegister = [boardObj];
    }
    const callbackURL = TRELLO_WEBHOOK_CALLBACK_URL;
    let anySuccess = false;
    for (const boardObj of boardsToRegister) {
      try {
        // Register webhook via backend (will reuse if exists)
        const response = await fetch(`${API_BASE_URL}/api/trello/webhooks`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            callbackURL,
            idModel: boardObj.id,
            description: `Webhook for ${selectedEvent} on ${boardObj.name}`,
            eventSettings: [{
              event_type: selectedEvent,
              enabled: true,
              extra_config: {
                label: selectedLabel,
                list_name: selectedList
              }
            }]
          })
        });
        if (!response.ok && response.status !== 200 && response.status !== 201) {
          let errMsg = 'Failed to register webhook';
          const contentType = response.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            const err = await response.json();
            errMsg = err.error || errMsg;
          } else {
            errMsg = await response.text();
          }
          throw new Error(errMsg);
        }
        const webhookData = await response.json();
        if (!webhookData.id) {
          console.error('No webhook_id returned from /trello/webhooks:', webhookData);
          toast({
            title: 'Webhook registration failed',
            description: 'No webhook_id returned from backend. Please try again or contact support.',
            variant: 'destructive'
          });
          continue;
        }
        // Always save a new WebhookSetting for each event/config
        await fetch(`${API_BASE_URL}/api/webhook-settings`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            board_id: boardObj.id,
            board_name: boardObj.name,
            event_type: selectedEvent,
            label: selectedLabel,
            list_name: selectedList,
            webhook_id: webhookData.id
          })
        });
        const newWebhook = {
          id: webhookData.id,
          event: selectedEvent,
          board: boardObj.name,
          status: 'active'
        };
        setWebhooks(prev => [...prev, newWebhook]);
        toast({
          title: "Webhook registered!",
          description: `Webhook for \"${selectedEvent}\" on \"${boardObj.name}\" has been created`,
        });
        anySuccess = true;
      } catch (err: any) {
        toast({
          title: `Webhook registration failed for ${boardObj.name}`,
          description: err.message || 'Could not register webhook with Trello.',
          variant: "destructive"
        });
      }
    }
    if (anySuccess) {
      // Reset form
      setSelectedEvent('');
      setSelectedBoard('');
      setSelectedList('');
      setSelectedLabel('');
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

  const handleDeleteWebhook = async (webhookId: string) => {
    try {
      // Deleting webhook: {webhookId}
      const resp = await fetch(`${API_BASE_URL}/api/webhook-settings/${webhookId}`, { 
        method: 'DELETE',
        credentials: 'include'
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.error || err.message || 'Failed to delete webhook');
      }
      
      // Refresh webhooks to update the display
      await fetchWebhooks();
      
      toast({
        title: 'Webhook deleted',
        description: `Webhook setting has been deleted.`,
      });
    } catch (err: any) {
      toast({
        title: 'Failed to delete webhook',
        description: err.message || 'Could not delete webhook.',
        variant: 'destructive',
      });
    }
  };

  const fetchWebhooks = async () => {
    if (!userEmail) {
      toast({
        title: "Missing user email",
        description: "Please log in to fetch webhooks.",
        variant: "destructive"
      });
      return;
    }
    try {
      // Fetch user's webhook settings from our database
      const response = await fetch(`${API_BASE_URL}/api/webhook-settings`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include'
      });
      const contentType = response.headers.get('content-type');
      let data;
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
        throw new Error(`Unexpected response: ${data}`);
      }
      
      // Group settings by webhook_id to show multiple events per webhook
      const webhookGroups = {};
      (data || []).forEach((setting: any) => {
        if (!webhookGroups[setting.webhook_id]) {
          webhookGroups[setting.webhook_id] = {
            id: setting.webhook_id,
            board: setting.board_name,
            board_id: setting.board_id,
            events: []
          };
        }
        webhookGroups[setting.webhook_id].events.push({
          id: setting.id,
          event_type: setting.event_type,
          label: setting.label,
          list_name: setting.list_name,
          status: 'active'
        });
      });
      
      // Convert to array format for display
      const groupedWebhooks = Object.values(webhookGroups).map((group: any) => ({
        id: group.id,
        board: group.board,
        board_id: group.board_id,
        events: group.events,
        status: 'active'
      }));
      
      setWebhooks(groupedWebhooks);
    } catch (err: any) {
      toast({
        title: "Failed to fetch webhooks",
        description: err.message || 'Could not fetch webhook settings.',
        variant: "destructive"
      });
    }
  };

  useEffect(() => {
    if (userEmail) {
      fetchWebhooks();
    }
    // eslint-disable-next-line
  }, [userEmail]);

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
                  <SelectValue placeholder="All Boards" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem key="__ALL__" value="__ALL__">
                    All Boards
                  </SelectItem>
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
              {webhooks.map((webhook, idx) => (
                <div key={webhook.id || idx} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      <Badge 
                        variant={webhook.status === 'active' ? 'default' : 'secondary'}
                        className={webhook.status === 'active' ? 'bg-green-500' : ''}
                      >
                        {webhook.status}
                      </Badge>
                      <div>
                        <p className="font-medium">Board: {webhook.board}</p>
                        <p className="text-sm text-gray-500">Webhook ID: {webhook.id}</p>
                      </div>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => handleDeleteWebhook(webhook.id)}>
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                  
                  {/* Events for this webhook */}
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-gray-700">Events:</p>
                    {webhook.events && webhook.events.map((event: any, eventIdx: number) => (
                      <div key={eventIdx} className="flex items-center justify-between bg-gray-50 p-2 rounded">
                        <div>
                          <p className="text-sm font-medium">{event.event_type}</p>
                          {(event.label || event.list_name) && (
                            <p className="text-xs text-gray-500">
                              {event.label && `Label: ${event.label}`}
                              {event.label && event.list_name && ' • '}
                              {event.list_name && `List: ${event.list_name}`}
                            </p>
                          )}
                        </div>
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          onClick={() => handleDeleteWebhook(event.id)}
                          className="text-red-500 hover:text-red-700"
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
