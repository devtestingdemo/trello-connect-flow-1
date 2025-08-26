
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

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

const saveUserCredentials = async (email: string, apiKey: string, token: string) => {
  const response = await fetch(`${API_BASE_URL}/api/users`, {
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
  const response = await fetch(`${API_BASE_URL}/api/users/${email}`);
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
  // Only keep apiKey/token in state for initial connect
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

  // Session-based login
  const handleSessionLogin = async (email: string) => {
    const resp = await fetch(`${API_BASE_URL}/api/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email })
    });
    if (!resp.ok) throw new Error('Login failed');
    setIsAuthenticated(true);
    setUserEmail(email);
    

  };

  // Session-based logout
  const handleSessionLogout = async () => {
    await fetch(`${API_BASE_URL}/api/logout`, {
      method: 'POST',
      credentials: 'include',
    });
    setIsAuthenticated(false);
    setUserEmail('');
    setApiKey('');
    setToken('');
    localStorage.removeItem('isAuthenticated');
    localStorage.removeItem('userEmail');
  };

  // After connect, clear apiKey/token from state
  const handleTrelloConnect = async (boards: any[]) => {
    setTrelloConnected(true);
    setTrelloBoards(boards);
          setApiKey('');
          setToken('');
    localStorage.removeItem('apiKey');
    localStorage.removeItem('token');
  };

  // After login, check if Trello is linked
  useEffect(() => {
    const checkTrelloLinked = async () => {
      if (!isAuthenticated) {
        setTrelloConnected(false);
        setTrelloBoards([]);
        return;
      }
      try {
        const res = await fetch(`${API_BASE_URL}/api/trello/verify`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
        });
        if (res.status === 400) {
          setTrelloConnected(false);
          setTrelloBoards([]);
          return;
        } else if (res.ok) {
          setTrelloConnected(true);
          // Now fetch boards
          const boardsRes = await fetch(`${API_BASE_URL}/api/trello/boards`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
          });
          if (!boardsRes.ok) throw new Error('Failed to fetch boards');
          const boardsData = await boardsRes.json();
          const boardsWithLists = boardsData.boards || [];
          setTrelloBoards(boardsWithLists);
        }
      } catch {
        setTrelloConnected(false);
        setTrelloBoards([]);
      }
    };
    checkTrelloLinked();
    // eslint-disable-next-line
  }, [isAuthenticated]);

  // Helper: should show Trello connection UI?
  const shouldShowTrelloConnect = isAuthenticated && !trelloConnected;

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
            onAuthSuccess={async (email) => {
              await handleSessionLogin(email);
            }}
            onSignOut={handleSessionLogout}
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
                      onConnectionSuccess={handleTrelloConnect}
                      userEmail={userEmail}
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
