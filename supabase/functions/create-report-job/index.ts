// Follow this setup guide to integrate the Deno language server with your editor:
// https://deno.land/manual/getting_started/setup_your_environment
// This enables autocomplete, go to definition, etc.

// Use imports defined in import_map.json
import { createClient, SupabaseClient } from "@supabase/supabase-js";
import { z } from "zod";
import { connect, Redis } from "redis"; // Import Redis using the map key

console.log("[Init] create-report-job Function started")

// --- Redis Initialization ---
let redis: Redis | null = null;
const redisQueueName = "new_report_jobs"; // Name of the list to push job IDs to

async function getRedisClient(): Promise<Redis> {
  // --- RESTORE REDIS LOGIC ---
  console.log("[Redis] Checking existing connection...");
  
  if (redis && redis.isConnected) {
    console.log("[Redis] Reusing existing connection");
    return redis;
  }
  
  // Configuration with fallback URLs
  const redisUrl = Deno.env.get("MY_REDIS_URL") || 
                   Deno.env.get("REDIS_URL") || 
                   "redis://host.docker.internal:6379";
  
  console.log(`[Redis] Using connection URL: ${redisUrl}`);
  
  try {
    // Extract hostname and port (basic parsing, assumes redis://host:port format)
    const urlParts = redisUrl.replace("redis://", "").split(':');
    const hostname = urlParts[0];
    const port = urlParts.length > 1 ? parseInt(urlParts[1], 10) : 6379;
    
    console.log(`[Redis] Attempting to connect to ${hostname}:${port} with 5s timeout...`);
    
    // Create connection with timeout
    const connectionPromise = connect({
      hostname: hostname,
      port: port,
      // Add password if your Redis requires it
      password: Deno.env.get("REDIS_PASSWORD") || undefined,
    });
    
    // Add timeout wrapper
    const timeoutPromise = new Promise<never>((_, reject) => {
      setTimeout(() => {
        reject(new Error(`Redis connection timeout after 5 seconds to ${hostname}:${port}`));
      }, 5000);
    });
    
    redis = await Promise.race([connectionPromise, timeoutPromise]);
    console.log(`[Redis] Connection successful to ${hostname}:${port}`);
    return redis;
    
  } catch (err) {
    console.error(`[Redis] Connection failed:`, err);
    redis = null; // Ensure client is null on failure
    
    // Provide more specific error messages
    if (err.message.includes('timeout')) {
      throw new Error(`Redis connection timeout - server may be unavailable`);
    } else if (err.message.includes('ECONNREFUSED')) {
      throw new Error(`Redis connection refused - check if Redis server is running`);
    } else {
      throw new Error(`Redis connection failed: ${err.message}`);
    }
  }
}
// --- End Redis Initialization ---

// Define the schema for the request body using Zod
const RequestBodySchema = z.object({
  report_type: z.string().min(1, { message: "Report type is required" }),
  report_parameters: z.record(z.unknown()).optional().default({}), // Ensure parameters is always an object
})

// Type for the data to be inserted into report_jobs
interface ReportJobInsert {
  user_id: string;
  report_type: string;
  report_parameters?: Record<string, unknown>;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  // Add other fields from your report_jobs table schema as needed
}

// Helper function to insert the job
async function createReportJob(supabaseClient: SupabaseClient, jobData: ReportJobInsert): Promise<{ data: any; error: any }> {
  const { data, error } = await supabaseClient
    .from('report_jobs')
    .insert([jobData])
    .select() // Select the created record to return its ID
    .single() // Expecting only one record to be created

  if (error) {
    console.error("Database insert error:", error)
    // Consider more specific error handling based on DB error codes if needed
  }

  return { data, error }
}

// Helper function to publish job ID to Redis
async function publishJobIdToQueue(jobId: number): Promise<{ success: boolean; error?: string }> {
  console.log(`[Redis Queue] Publishing job ID ${jobId} to queue '${redisQueueName}'...`);
  
  try {
    const redisClient = await getRedisClient();
    console.log(`[Redis Queue] Got Redis client, executing LPUSH...`);
    
    // LPUSH adds the job ID to the beginning of the list
    const result = await redisClient.lpush(redisQueueName, jobId.toString()); 
    console.log(`[Redis Queue] Successfully published job ID ${jobId}. Queue length: ${result}`);
    
    return { success: true };
  } catch (err) {
    const errorMsg = `Failed to publish job ID ${jobId} to Redis queue: ${err.message}`;
    console.error(`[Redis Queue] ${errorMsg}`, err);
    
    return { 
      success: false, 
      error: errorMsg
    };
  }
}

Deno.serve(async (req) => {
  // ** REMOVE DIAGNOSTIC LOG **
  // console.log(`[DIAGNOSTIC] Value of Deno.env.get("MY_REDIS_URL"): ${Deno.env.get("MY_REDIS_URL")}`);
  // Handle CORS preflight requests
  const origin = req.headers.get('origin');
  const allowedOrigins = [
    'http://localhost:3000',
    'http://localhost:3001', 
    'https://localhost:3000',
    'https://localhost:3001',
    // Add production domains here
    Deno.env.get('FRONTEND_URL')
  ].filter(Boolean); // Remove undefined values
  
  const corsHeaders = {
    'Access-Control-Allow-Origin': allowedOrigins.includes(origin) ? origin : 'http://localhost:3000',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
    'Access-Control-Max-Age': '3600', // Cache preflight for 1 hour
  }
  
  console.log(`[CORS] Request origin: ${origin}, Allowed: ${corsHeaders['Access-Control-Allow-Origin']}`);
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // 1. Initialize Supabase client (with auth context)
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_ANON_KEY') ?? '',
      { global: { headers: { Authorization: req.headers.get('Authorization')! } } }
    )

    // 2. Get the user object
    const { data: { user }, error: authError } = await supabaseClient.auth.getUser()

    if (authError || !user) {
      console.error('Auth error:', authError?.message)
      return new Response(
        JSON.stringify({ error: 'Unauthorized: ' + (authError?.message || 'User not found') }),
        { status: 401, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
      )
    }
    console.log(`Authenticated user ID: ${user.id}`)

    // 3. Parse and validate the request body
    let body;
    try {
      body = await req.json();
    } catch (parseError) {
      console.error('JSON Parsing error:', parseError.message);
      return new Response(
        JSON.stringify({ error: 'Invalid JSON body' }),
        { status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
      );
    }

    const validationResult = RequestBodySchema.safeParse(body)
    if (!validationResult.success) {
      console.error('Validation errors:', validationResult.error.flatten())
      return new Response(
        JSON.stringify({ error: 'Invalid request body', details: validationResult.error.flatten() }),
        { status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
      )
    }
    const { report_type, report_parameters } = validationResult.data
    console.log(`Validated request: Type=${report_type}, Params=`, report_parameters)

    // 4. Create the report job in the database
    const newJobData: ReportJobInsert = {
      user_id: user.id,
      report_type: report_type,
      report_parameters: report_parameters,
      status: 'pending',
      // TODO: Add logic for credit checking/deduction here (Subtask 21)
    }

    const { data: createdJob, error: dbError } = await createReportJob(supabaseClient, newJobData)

    if (dbError || !createdJob) {
      return new Response(
        JSON.stringify({ error: 'Failed to create report job', details: dbError?.message || 'Unknown database error' }),
        { status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
      )
    }

    console.log(`Successfully created job ID: ${createdJob.id}`) 

    // 5. Publish Job ID to Redis (Restored)
    console.log(`[Main] Publishing job ID ${createdJob.id} to Redis queue...`);
    const publishResult = await publishJobIdToQueue(createdJob.id);
    
    if (!publishResult.success) {
      console.error(`[Main] CRITICAL: Failed to publish job ID ${createdJob.id} to Redis queue. Error: ${publishResult.error}`);
      
      // Return detailed error to user
      return new Response(
        JSON.stringify({ 
          error: 'Job created but failed to queue for processing. Please try again.',
          details: publishResult.error,
          jobId: createdJob.id 
        }), 
        { status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
      );
    }
    
    console.log(`[Main] Successfully queued job ID ${createdJob.id} for processing`);

    // 6. Return success response
    const responseData = {
      message: `Report job successfully created with ID: ${createdJob.id} and queued for processing.`,
      jobId: createdJob.id,
      status: createdJob.status,
    }

    return new Response(
      JSON.stringify(responseData),
      { status: 201, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
    )

  } catch (error) {
    console.error('[Main] Unhandled error in create-report-job function:', error)
    
    // Provide more specific error messages based on error type
    let errorMessage = 'Internal Server Error';
    let details = error.message || 'Unknown error occurred';
    
    if (error.message?.includes('Redis')) {
      errorMessage = 'Database queue service unavailable';
      details = 'Unable to queue job for processing. Please try again in a few moments.';
    } else if (error.message?.includes('Unauthorized')) {
      errorMessage = 'Authentication failed';
      details = 'Please log in and try again.';
    } else if (error.message?.includes('timeout')) {
      errorMessage = 'Service timeout';
      details = 'Request took too long to process. Please try again.';
    }
    
    return new Response(
      JSON.stringify({ 
        error: errorMessage, 
        details: details,
        timestamp: new Date().toISOString()
      }),
      { status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders } }
    )
  }
})

/* To invoke locally:

  1. Run `supabase start`
  2. Make an HTTP request (ensure you have a valid user JWT):

  curl -i --location --request POST 'http://127.0.0.1:54321/functions/v1/create-report-job' \\\
    --header 'Authorization: Bearer YOUR_USER_JWT' \\\
    --header 'Content-Type: application/json' \\\
    --data '{"report_type":"example_report", "report_parameters": {"param1":"value1"}}'

*/
