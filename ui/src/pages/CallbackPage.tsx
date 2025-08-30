import { useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useToast } from "@/hooks/use-toast";
import { setAuthToken, authApi } from "@/lib/api";

interface CallbackPageProps {
  onLogin: (user: any) => void;
}

export default function CallbackPage({ onLogin }: CallbackPageProps) {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { toast } = useToast();

  useEffect(() => {
    const handleCallback = async () => {
      const success = searchParams.get("success");
      const token = searchParams.get("token");
      const error = searchParams.get("error");

      if (error) {
        toast({
          title: "Authentication failed",
          description: "Google authentication was cancelled or failed.",
          variant: "destructive",
        });
        navigate("/auth");
        return;
      }

      if (success === "true" && token) {
        try {
          // Set the token and get user data
          setAuthToken(token);
          const response = await authApi.getCurrentUser();

          if (response.status === "success" && response.data) {
            onLogin(response.data);
            toast({
              title: "Welcome!",
              description: `Successfully signed in with Google.`,
            });
            navigate("/dashboard");
          } else {
            throw new Error("Failed to get user data");
          }
        } catch (error) {
          toast({
            title: "Authentication failed",
            description:
              error instanceof Error ? error.message : "Something went wrong",
            variant: "destructive",
          });
          navigate("/auth");
        }
        return;
      }

      // Fallback for traditional OAuth flow
      const code = searchParams.get("code");
      const state = searchParams.get("state");

      if (!code) {
        toast({
          title: "Authentication failed",
          description: "No authorization code received.",
          variant: "destructive",
        });
        navigate("/auth");
        return;
      }

      try {
        // The backend callback endpoint should handle the code exchange
        const response = await fetch(
          `${
            import.meta.env.VITE_API_URL
          }/auth/google/callback?code=${code}&state=${state}`,
          {
            method: "GET",
            credentials: "include",
          }
        );

        const data = await response.json();

        if (data.status === "success" && data.data) {
          setAuthToken(data.data.tokens.access_token);
          onLogin(data.data.user);
          toast({
            title: "Welcome!",
            description: `Successfully signed in with Google.`,
          });
          navigate("/dashboard");
        } else {
          throw new Error(data.error?.message || "Authentication failed");
        }
      } catch (error) {
        toast({
          title: "Authentication failed",
          description:
            error instanceof Error ? error.message : "Something went wrong",
          variant: "destructive",
        });
        navigate("/auth");
      }
    };

    handleCallback();
  }, [searchParams, navigate, toast, onLogin]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
        <p className="text-muted-foreground">Completing Google sign-in...</p>
      </div>
    </div>
  );
}
