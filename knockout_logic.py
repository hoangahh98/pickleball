"""
Match Scheduling Logic - Support both Singles and Doubles
+ Round-robin format
+ Matches distributed across available courts
"""

class MatchSchedulerService:
    """Generate match schedules"""
    
    @staticmethod
    def generate_round_robin(teams, num_courts, match_type='don'):
        """
        Generate round-robin schedule
        
        Args:
            teams: List of team/player names
            num_courts: Number of courts available
            match_type: 'don' (singles) or 'doi' (doubles)
        
        Returns:
            List of matches: [{'doi_a': '', 'doi_b': '', 'san': 1, 'vong': 1}, ...]
        """
        
        if match_type == 'doi':
            # Doubles: Pair players, then do round-robin with pairs
            pairs = MatchSchedulerService._create_pairs(teams)
            if not pairs:
                return []
            return MatchSchedulerService._round_robin_doubles(pairs, num_courts)
        else:
            # Singles: Direct round-robin
            return MatchSchedulerService._round_robin_singles(teams, num_courts)
    
    @staticmethod
    def _create_pairs(teams):
        """Create pairs from list of players for doubles"""
        if len(teams) < 2:
            return []
        
        pairs = []
        for i in range(0, len(teams) - 1, 2):
            pair = f"{teams[i]} + {teams[i+1]}"
            pairs.append(pair)
        
        # If odd number, last player paired with first
        if len(teams) % 2 == 1:
            pair = f"{teams[-1]} + {teams[0]}"
            pairs.append(pair)
        
        return pairs
    
    @staticmethod
    def _round_robin_singles(teams, num_courts):
        """Round-robin for singles (1v1)"""
        matches = []
        n = len(teams)
        
        # Round-robin algorithm
        for vong in range(n - 1):
            round_matches = []
            for i in range(n // 2):
                team_a = teams[i]
                team_b = teams[n - 1 - i]
                round_matches.append({
                    'doi_a': team_a,
                    'doi_b': team_b,
                    'san': (i % num_courts) + 1,
                    'vong': vong + 1
                })
            
            # Rotate for next round
            if vong < n - 2:
                teams = [teams[0]] + teams[-1:] + teams[1:-1]
            
            matches.extend(round_matches)
        
        return matches
    
    @staticmethod
    def _round_robin_doubles(pairs, num_courts):
        """Round-robin for doubles (2v2)"""
        matches = []
        n = len(pairs)
        
        # Round-robin algorithm
        for vong in range(n - 1):
            round_matches = []
            for i in range(n // 2):
                pair_a = pairs[i]
                pair_b = pairs[n - 1 - i]
                round_matches.append({
                    'doi_a': pair_a,
                    'doi_b': pair_b,
                    'san': (i % num_courts) + 1,
                    'vong': vong + 1
                })
            
            # Rotate for next round
            if vong < n - 2:
                pairs = [pairs[0]] + pairs[-1:] + pairs[1:-1]
            
            matches.extend(round_matches)
        
        return matches