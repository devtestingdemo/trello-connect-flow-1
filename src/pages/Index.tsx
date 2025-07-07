
import React, { useState } from 'react';
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

const Index = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userEmail, setUserEmail] = useState('');
  const [trelloConnected, setTrelloConnected] = useState(false);
  const [trelloBoards, setTrelloBoards] = useState([]);

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
                  <TrelloConnectionSection 
                    onConnectionSuccess={(boards) => {
                      setTrelloConnected(true);
                      setTrelloBoards(boards);
                    }}
                  />
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
