import { getRepositoryLog, runGitCommand, fetchCommitData } from "./gitService.js";

export async function semanticSearch(query, cwd, options = {}) {
  const { limit = 50, author, since, until } = options;
  
  // Get repository log
  const logOutput = getRepositoryLog(cwd, limit);
  const commits = parseLogOutput(logOutput);
  
  // Filter by author if specified
  const filteredCommits = author 
    ? commits.filter(commit => commit.author.toLowerCase().includes(author.toLowerCase()))
    : commits;
  
  // Filter by date range if specified
  const dateFilteredCommits = filterByDateRange(filteredCommits, since, until);
  
  if (dateFilteredCommits.length === 0) {
    return {
      results: [],
      query,
      total: 0
    };
  }
  
  // Use text-based search for now (can be enhanced with AI later)
  return fallbackTextSearch(query, dateFilteredCommits);
}

export async function patternSearch(pattern, cwd, options = {}) {
  const { limit = 50, filePattern, caseInsensitive = false } = options;
  
  // Search git log for commits that match the pattern
  const grepArgs = ['log', '--all', '--grep', pattern, '--pretty=format:%h %ad %an %s'];
  
  if (limit) {
    grepArgs.push(`--max-count=${limit}`);
  }
  
  if (caseInsensitive) {
    grepArgs.push('--regexp-ignore-case');
  }
  
  try {
    const logOutput = runGitCommand(grepArgs, cwd);
    const commits = parseLogOutput(logOutput);
    
    // If file pattern specified, also search for changes in specific files
    let fileFilteredCommits = commits;
    if (filePattern) {
      fileFilteredCommits = await filterByFilePattern(commits, filePattern, cwd);
    }
    
    return {
      results: fileFilteredCommits.map(commit => ({
        sha: commit.sha,
        message: commit.message,
        author: commit.author,
        date: commit.date,
        matchType: 'message'
      })),
      pattern,
      total: fileFilteredCommits.length
    };
  } catch (error) {
    return {
      results: [],
      pattern,
      total: 0,
      error: error.message
    };
  }
}

export async function codePatternSearch(pattern, cwd, options = {}) {
  const { limit = 20, fileType } = options;
  
  // Search for commits that introduced changes matching the code pattern
  const grepArgs = ['log', '--all', '-S', pattern, '--pretty=format:%h %ad %an %s'];
  
  if (limit) {
    grepArgs.push(`--max-count=${limit}`);
  }
  
  if (fileType) {
    grepArgs.push(`--`, `*.${fileType}`);
  }
  
  try {
    const logOutput = runGitCommand(grepArgs, cwd);
    const commits = parseLogOutput(logOutput);
    
    // Get diff for each commit to show matching lines
    const resultsWithDiff = await Promise.all(
      commits.slice(0, 10).map(async commit => {
        try {
          const commitData = await fetchCommitData(commit.sha, cwd);
          return {
            sha: commit.sha,
            message: commit.message,
            author: commit.author,
            date: commit.date,
            diff: commitData.diff.substring(0, 500), // First 500 chars
            matchType: 'code'
          };
        } catch {
          return {
            sha: commit.sha,
            message: commit.message,
            author: commit.author,
            date: commit.date,
            diff: '',
            matchType: 'code'
          };
        }
      })
    );
    
    return {
      results: resultsWithDiff,
      pattern,
      total: commits.length
    };
  } catch (error) {
    return {
      results: [],
      pattern,
      total: 0,
      error: error.message
    };
  }
}

export async function authorActivityTimeline(author, cwd, options = {}) {
  const { since, until, granularity = 'daily' } = options;
  
  // Get all commits by author
  const logArgs = ['log', '--all', '--author', author, '--pretty=format:%h %ad %an %s', '--date=iso'];
  
  if (since) logArgs.push(`--since=${since}`);
  if (until) logArgs.push(`--until=${until}`);
  
  try {
    const logOutput = runGitCommand(logArgs, cwd);
    const commits = parseLogOutput(logOutput);
    
    // Group commits by time period
    const timeline = groupByTimePeriod(commits, granularity);
    
    // Calculate statistics
    const stats = {
      totalCommits: commits.length,
      dateRange: getDateRange(commits),
      averagePerPeriod: calculateAveragePerPeriod(timeline),
      mostActivePeriod: getMostActivePeriod(timeline)
    };
    
    return {
      author,
      timeline,
      stats,
      granularity
    };
  } catch (error) {
    return {
      author,
      timeline: [],
      stats: null,
      error: error.message
    };
  }
}

function parseLogOutput(output) {
  if (!output) return [];
  
  return output.split('\n').filter(line => line.trim()).map(line => {
    const parts = line.split(' ');
    const sha = parts[0];
    const date = parts[1];
    const author = parts.slice(2, -1).join(' ');
    const message = parts[parts.length - 1];
    
    return { sha, date, author, message };
  });
}

function filterByDateRange(commits, since, until) {
  if (!since && !until) return commits;
  
  return commits.filter(commit => {
    const commitDate = new Date(commit.date);
    if (since && commitDate < new Date(since)) return false;
    if (until && commitDate > new Date(until)) return false;
    return true;
  });
}

function fallbackTextSearch(query, commits) {
  const queryLower = query.toLowerCase();
  const keywords = queryLower.split(/\s+/).filter(word => word.length > 2);
  
  const results = commits.filter(commit => 
    keywords.some(keyword => 
      commit.message.toLowerCase().includes(keyword)
    )
  ).map(commit => ({
    sha: commit.sha,
    message: commit.message,
    author: commit.author,
    date: commit.date,
    relevance: calculateRelevance(commit.message, keywords)
  })).sort((a, b) => b.relevance - a.relevance);
  
  return {
    results,
    query,
    total: results.length,
    fallback: true
  };
}

function calculateRelevance(message, keywords) {
  const messageLower = message.toLowerCase();
  let score = 0;
  
  keywords.forEach(keyword => {
    if (messageLower.includes(keyword)) {
      score += keyword.length; // Longer keywords get more weight
    }
  });
  
  return score;
}

async function filterByFilePattern(commits, filePattern, cwd) {
  const filtered = [];
  
  for (const commit of commits) {
    try {
      const files = runGitCommand(['diff', '--name-only', `${commit.sha}^..${commit.sha}`], cwd);
      if (files.includes(filePattern) || files.match(new RegExp(filePattern))) {
        filtered.push(commit);
      }
    } catch {
      // Skip if we can't get file list
      filtered.push(commit);
    }
  }
  
  return filtered;
}

function groupByTimePeriod(commits, granularity) {
  const groups = {};
  
  commits.forEach(commit => {
    const date = new Date(commit.date);
    let key;
    
    switch (granularity) {
      case 'hourly':
        key = date.toISOString().substring(0, 13); // YYYY-MM-DDTHH
        break;
      case 'daily':
        key = date.toISOString().substring(0, 10); // YYYY-MM-DD
        break;
      case 'weekly':
        const weekStart = new Date(date);
        weekStart.setDate(date.getDate() - date.getDay());
        key = weekStart.toISOString().substring(0, 10);
        break;
      case 'monthly':
        key = date.toISOString().substring(0, 7); // YYYY-MM
        break;
      default:
        key = date.toISOString().substring(0, 10);
    }
    
    if (!groups[key]) {
      groups[key] = {
        period: key,
        commits: [],
        count: 0
      };
    }
    
    groups[key].commits.push(commit);
    groups[key].count++;
  });
  
  return Object.values(groups).sort((a, b) => a.period.localeCompare(b.period));
}

function getDateRange(commits) {
  if (commits.length === 0) return null;
  
  const dates = commits.map(c => new Date(c.date));
  return {
    start: new Date(Math.min(...dates)).toISOString().substring(0, 10),
    end: new Date(Math.max(...dates)).toISOString().substring(0, 10)
  };
}

function calculateAveragePerPeriod(timeline) {
  if (timeline.length === 0) return 0;
  
  const total = timeline.reduce((sum, period) => sum + period.count, 0);
  return (total / timeline.length).toFixed(1);
}

function getMostActivePeriod(timeline) {
  if (timeline.length === 0) return null;
  
  return timeline.reduce((max, period) => 
    period.count > max.count ? period : max
  );
}
