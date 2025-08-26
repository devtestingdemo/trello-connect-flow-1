
import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Mail, CheckCircle } from "lucide-react";
import { jwtDecode } from "jwt-decode";

interface GoogleAuthSectionProps {
  isAuthenticated: boolean;
  userEmail: string;
  onAuthSuccess: (email: string) => void;
  onSignOut: () => void; // <-- add this
}

export const GoogleAuthSection: React.FC<GoogleAuthSectionProps> = ({
  isAuthenticated,
  userEmail,
  onAuthSuccess,
  onSignOut
}) => {
  const googleButtonRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    
    // Wait for both Google library and DOM element to be ready
    const initializeGoogleAuth = () => {
      if (!isAuthenticated && (window as any).google && googleButtonRef.current && clientId) {
        try {
          (window as any).google.accounts.id.initialize({
            client_id: clientId,
            callback: (response: any) => {
              // Decode JWT to get user info, or use Google's API to fetch profile
              const userObject = jwtDecode<{ email: string }>(response.credential);
              onAuthSuccess(userObject.email);
            }
          });
          
          (window as any).google.accounts.id.renderButton(googleButtonRef.current, {
            theme: "outline",
            size: "large"
          });
          
          console.log('Google button rendered successfully');
        } catch (error) {
          console.error('Error rendering Google button:', error);
        }
      }
    };

    // Try immediately
    initializeGoogleAuth();
    
    // If not ready, wait a bit and try again
    if (!(window as any).google || !googleButtonRef.current) {
      const timer = setTimeout(initializeGoogleAuth, 1000);
      return () => clearTimeout(timer);
    }
  }, [isAuthenticated, onAuthSuccess]);

  if (isAuthenticated) {
    return (
      <Card className="bg-green-50 border-green-200">
        <CardContent className="p-6">
          <div className="flex items-center space-x-3">
            <CheckCircle className="w-6 h-6 text-green-600" />
            <div>
              <h3 className="text-lg font-semibold text-green-800">Successfully Authenticated</h3>
              <div className="flex items-center space-x-2 mt-1">
                <Mail className="w-4 h-4 text-green-600" />
                <span className="text-sm text-green-700">{userEmail}</span>
              </div>
            </div>
          </div>
          <Button onClick={onSignOut} variant="outline" className="mt-4">
            Sign Out
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!isAuthenticated) {
    return (
      <Card className="bg-white shadow-sm">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Welcome</CardTitle>
          <CardDescription>
            Sign in to connect your Trello account
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* App-styled label above Google button */}
          <div className="text-base font-sans font-medium text-gray-900 text-center">Sign in with Google</div>
          <div ref={googleButtonRef}></div>
          <p className="text-xs text-gray-500 text-center">
            By signing in, you agree to our terms of service and privacy policy
          </p>
        </CardContent>
      </Card>
    );
  }
};
