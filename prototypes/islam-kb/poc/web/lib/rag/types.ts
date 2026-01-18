export interface SearchResult {
  text: string;
  book: string;
  page: number;
  score: number;
}

export interface Source {
  id: string;
  book: string;
  page: number;
  score: number;
  text: string;
}

export interface ConversationTurn {
  question: string;
  answer: string;
}
