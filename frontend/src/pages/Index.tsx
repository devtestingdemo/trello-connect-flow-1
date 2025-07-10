
import React, { useState, useEffect } from 'react';
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { GoogleAuthSection } from "@/components/GoogleAuthSection";
import { TrelloConnectionSection } from "@/components/TrelloConnectionSection";
import { WebhookManagementSection } from "@/components/WebhookManagementSection";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const saveUserCredentials = async (email: string, apiKey: string, token: string) => {
  const response = await fetch(`${API_BASE_URL}/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, apiKey, token }),
  });
  if (!response.ok) {
    throw new Error('Failed to save user');
  }
  return await response.json();
};

const getUserCredentials = async (email: string) => {
  const response = await fetch(`${API_BASE_URL}/users/${email}`);
  if (!response.ok) {
    throw new Error('User not found');
  }
  return await response.json();
};

const Index = () => {
  // Restore auth state from localStorage if available
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    const stored = localStorage.getItem('isAuthenticated');
    return stored === 'true';
  });
  const [userEmail, setUserEmail] = useState(() => {
    return localStorage.getItem('userEmail') || '';
  });
  const [trelloConnected, setTrelloConnected] = useState(false);
  const [trelloBoards, setTrelloBoards] = useState([]);
  const [apiKey, setApiKey] = useState('');
  const [token, setToken] = useState('');

  // Persist auth state to localStorage
  useEffect(() => {
    localStorage.setItem('isAuthenticated', isAuthenticated ? 'true' : 'false');
    if (userEmail) {
      localStorage.setItem('userEmail', userEmail);
    } else {
      localStorage.removeItem('userEmail');
    }
  }, [isAuthenticated, userEmail]);

  // Load credentials from backend if userEmail is set
  useEffect(() => {
    if (userEmail) {
      getUserCredentials(userEmail)
        .then((data) => {
          setApiKey(data.apiKey);
          setToken(data.token);
        })
        .catch(() => {
          setApiKey('');
          setToken('');
        });
    }
    // eslint-disable-next-line
  }, [userEmail]);

  // Automatically connect Trello if apiKey and token are present
  useEffect(() => {
    const fetchBoards = async () => {
      if (apiKey && token) {
        try {
          const boardsRes = await fetch(`https://api.trello.com/1/members/me/boards?key=${apiKey}&token=${token}`);
          if (!boardsRes.ok) throw new Error('Failed to fetch boards');
          const boardsData = await boardsRes.json();
          // For each board, fetch its lists
          const boardsWithLists = await Promise.all(
            boardsData.map(async (board) => {
              const listsRes = await fetch(`https://api.trello.com/1/boards/${board.id}/lists?key=${apiKey}&token=${token}`);
              const listsData = listsRes.ok ? await listsRes.json() : [];
              return {
                id: board.id,
                name: board.name,
                lists: listsData.map((list) => list.name)
              };
            })
          );
          setTrelloBoards(boardsWithLists);
          setTrelloConnected(true);
        } catch {
          setTrelloBoards([]);
          setTrelloConnected(false);
        }
      } else {
        setTrelloBoards([]);
        setTrelloConnected(false);
      }
    };
    fetchBoards();
    // eslint-disable-next-line
  }, [apiKey, token]);

  // Helper: should show Trello connection UI?
  const shouldShowTrelloConnect = !trelloConnected;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Trello Connect Flow
          </h1>
          <p className="text-lg text-gray-600">
            Streamline your Trello workflow with automated integrations
          </p>
        </div>

        {/* Main Content */}
        <div className="space-y-6">
          {/* Authentication Section */}
          <GoogleAuthSection 
            isAuthenticated={isAuthenticated}
            userEmail={userEmail}
            onAuthSuccess={(email) => {
              setIsAuthenticated(true);
              setUserEmail(email);
            }}
            onSignOut={() => {
              setIsAuthenticated(false);
              setUserEmail('');
              // @ts-ignore: google is injected by Google Identity Services
              if (window.google && window.google.accounts && window.google.accounts.id) {
                // @ts-ignore
                window.google.accounts.id.disableAutoSelect();
              }
              setApiKey('');
              setToken('');
              // Clear persisted auth state
              localStorage.removeItem('isAuthenticated');
              localStorage.removeItem('userEmail');
            }}
          />

          {/* Trello Integration Sections - Only show when authenticated */}
          {isAuthenticated && (
            <Accordion type="single" collapsible className="space-y-4">
              {/* Trello Connection */}
              <AccordionItem value="trello-connection" className="border rounded-lg bg-white shadow-sm">
                <AccordionTrigger className="px-6 py-4 hover:no-underline">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-semibold">
                      1
                    </div>
                    <div className="text-left">
                      <h3 className="text-lg font-semibold">Connect Trello</h3>
                      <p className="text-sm text-gray-500">Link your Trello account to get started</p>
                    </div>
                    {trelloConnected && (
                      <Badge variant="secondary" className="bg-green-100 text-green-800">
                        Connected
                      </Badge>
                    )}
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-6 pb-6">
                  {/* Only show connection UI if not already connected */}
                  {shouldShowTrelloConnect ? (
                    <TrelloConnectionSection 
                      apiKey={apiKey}
                      setApiKey={setApiKey}
                      token={token}
                      setToken={setToken}
                      onConnectionSuccess={async (boards) => {
                        setTrelloConnected(true);
                        setTrelloBoards(boards);
                        if (userEmail && apiKey && token) {
                          try {
                            await saveUserCredentials(userEmail, apiKey, token);
                          } catch (e) {
                            // Optionally handle error
                          }
                        }
                      }}
                    />
                  ) : (
                    <div className="text-green-700 font-medium">Trello connection established. You can now register webhooks.</div>
                  )}
                </AccordionContent>
              </AccordionItem>

              {/* Webhook Management */}
              <AccordionItem value="webhook-management" className="border rounded-lg bg-white shadow-sm">
                <AccordionTrigger className="px-6 py-4 hover:no-underline">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-purple-500 text-white rounded-full flex items-center justify-center font-semibold">
                      2
                    </div>
                    <div className="text-left">
                      <h3 className="text-lg font-semibold">Webhook Management</h3>
                      <p className="text-sm text-gray-500">Configure and manage Trello webhooks</p>
                    </div>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-6 pb-6">
                  <WebhookManagementSection 
                    trelloBoards={trelloBoards}
                    trelloConnected={trelloConnected}
                    apiKey={apiKey}
                    token={token}
                    userEmail={userEmail}
                  />
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          )}
        </div>

        {/* Footer */}
        <div className="mt-12 text-center text-gray-500 text-sm">
          <p>Secure integration with Trello API • Built with modern web technologies</p>
        </div>
      </div>
    </div>
  );
};

export default Index;
