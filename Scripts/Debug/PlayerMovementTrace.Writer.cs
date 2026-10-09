using System;
using System.Collections.Concurrent;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading.Tasks;

public partial class PlayerMovementTrace
{
    // Only strings cross the thread boundary; no Godot calls on the writer thread.
    private sealed class TraceWriter
    {
        public string LatestPath { get; }
        public string ArchivePath { get; }
        public volatile string Error;
        private readonly BlockingCollection<string> _queue = new(8192);
        private readonly Task _task;

        public TraceWriter(string directory, string latest, string archive)
        {
            LatestPath = Path.Combine(directory, latest);
            ArchivePath = Path.Combine(directory, archive);
            try
            {
                Directory.CreateDirectory(directory);
                var current = Open(LatestPath, FileMode.Create);
                StreamWriter history;
                try { history = Open(ArchivePath, FileMode.CreateNew); }
                catch { current.Dispose(); throw; }
                _task = Task.Run(() => WriteLoop(current, history));
            }
            catch (Exception e) { Error = e.Message; }
        }

        private static StreamWriter Open(string path, FileMode mode) => new(
            new FileStream(path, mode, FileAccess.Write, FileShare.ReadWrite, 65536), new UTF8Encoding(false), 65536);

        public void Enqueue(string line)
        {
            if (Error != null || _queue.IsAddingCompleted) return;
            if (!_queue.TryAdd(line)) Error = "Trace queue overflow: recording incomplete";
        }

        private void WriteLoop(StreamWriter current, StreamWriter history)
        {
            using (current)
            using (history)
            {
                try
                {
                    var clock = Stopwatch.StartNew();
                    bool dirty = false;
                    while (!_queue.IsCompleted)
                    {
                        if (_queue.TryTake(out string line, 100))
                        {
                            current.WriteLine(line);
                            history.WriteLine(line);
                            dirty = true;
                        }
                        if (clock.ElapsedMilliseconds >= 500)
                        {
                            if (dirty) { current.Flush(); history.Flush(); dirty = false; }
                            clock.Restart();
                        }
                    }
                    current.Flush(); history.Flush();
                }
                catch (Exception e) { Error = e.Message; }
            }
        }

        public void Finish()
        {
            _queue.CompleteAdding();
            if (_task != null && !_task.Wait(TimeSpan.FromSeconds(3))) Error = "Trace writer shutdown timeout";
        }
    }
}
