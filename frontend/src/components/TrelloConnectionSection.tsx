
import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ExternalLink, Loader2, Trello } from "lucide-react";
import { toast } from "@/hooks/use-toast";
import { useEffect } from 'react';

interface TrelloConnectionSectionProps {
  onConnectionSuccess: (boards: any[]) => void;
  apiKey: string;
  setApiKey: (key: string) => void;
  token: string;
  setToken: (token: string) => void;
}

export const TrelloConnectionSection: React.FC<TrelloConnectionSectionProps> = ({
  onConnectionSuccess,
  apiKey,
  setApiKey,
  token,
  setToken
}) => {
  const [isConnecting, setIsConnecting] = useState(false);
  const [boards, setBoards] = useState([]);
  const [userBoard, setUserBoard] = useState(null);

  const handleConnect = async () => {
    if (!apiKey || !token) {
      toast({
        title: "Missing credentials",
        description: "Please provide both API Key and Token",
        variant: "destructive"
      });
      return;
    }

    setIsConnecting(true);

    try {
      // Verify credentials by fetching the user's info
      const userRes = await fetch(`https://api.trello.com/1/members/me?key=${apiKey}&token=${token}`);
      if (!userRes.ok) {
        throw new Error("Invalid API Key or Token");
      }
      const user = await userRes.json();
      const userEmail = user.email || user.username || user.id;

      // Fetch boards
      const boardsRes = await fetch(`https://api.trello.com/1/members/me/boards?key=${apiKey}&token=${token}`);
      if (!boardsRes.ok) {
        throw new Error("Failed to fetch boards");
      }
      const boardsData = await boardsRes.json();

      // For each board, fetch its lists
      const boardsWithLists = await Promise.all(
        boardsData.map(async (board: any) => {
          const listsRes = await fetch(`https://api.trello.com/1/boards/${board.id}/lists?key=${apiKey}&token=${token}`);
          const listsData = listsRes.ok ? await listsRes.json() : [];
          return {
            id: board.id,
            name: board.name,
            lists: listsData.map((list: any) => list.name)
          };
        })
      );

      setBoards(boardsWithLists);
      onConnectionSuccess(boardsWithLists);
      setIsConnecting(false);

      toast({
        title: "Successfully connected!",
        description: `Found ${boardsWithLists.length} Trello boards`,
      });

      // Call backend to setup board and lists if not already present
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
      const setupRes = await fetch(`${API_BASE_URL}/trello/setup-board`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: userEmail, apiKey, token })
      });
      const setupData = await setupRes.json();
      if (setupRes.ok && setupData.board) {
        setUserBoard(setupData.board);
        toast({
          title: 'Board Ready',
          description: `Board: ${setupData.board.board_name} (Default list: Enquiry In)`
        });
      } else if (!setupRes.ok) {
        toast({
          title: 'Board Setup Failed',
          description: setupData.error || 'Could not setup Trello board',
          variant: 'destructive'
        });
      }
    } catch (err: any) {
      setIsConnecting(false);
      toast({
        title: "Connection failed",
        description: err.message || "Could not connect to Trello. Please check your credentials.",
        variant: "destructive"
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
        <p className="text-sm text-blue-800 mb-2">
          <strong>Step 1:</strong> Get your Trello API credentials
        </p>
        <Button variant="outline" size="sm" asChild>
          <a href="https://trello.com/app-key" target="_blank" rel="noopener noreferrer">
            <ExternalLink className="w-4 h-4 mr-2" />
            Get Trello API Key & Token
          </a>
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-2">
          <Label htmlFor="trello-api-key">Trello API Key</Label>
          <Input
            id="trello-api-key"
            placeholder="Enter your Trello API Key"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            type="password"
          />
        </div>
        
        <div className="space-y-2">
          <Label htmlFor="trello-token">Trello Token</Label>
          <Input
            id="trello-token"
            placeholder="Enter your Trello Token"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            type="password"
          />
        </div>
      </div>

      <Button 
        onClick={handleConnect} 
        disabled={isConnecting || !apiKey || !token}
        className="w-full"
        size="lg"
      >
        {isConnecting ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Connecting to Trello...
          </>
        ) : (
          <>
            <Trello className="w-4 h-4 mr-2" />
            Connect Trello
          </>
        )}
      </Button>

      {boards.length > 0 && (
        <div className="space-y-3">
          <h4 className="font-semibold text-gray-900">Your Trello Boards:</h4>
          <div className="grid gap-3">
            {boards.map((board: any) => (
              <Card key={board.id} className="p-4">
                <CardContent className="p-0">
                  <div className="flex items-center justify-between">
                    <div>
                      <h5 className="font-medium">{board.name}</h5>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {board.lists.map((list: string, index: number) => (
                          <Badge key={index} variant="secondary" className="text-xs">
                            {list}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
