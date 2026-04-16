import { cn } from "@/lib/utils";
import styles from "./user-jobs.module.css";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";
import { Briefcase, MapPin, Search, Loader2, Info } from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";

interface Job {
  id: string;
  title_raw: string;
  status: string;
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [location, setLocation] = useState("");
  const [minSalary, setMinSalary] = useState("");
  const [role, setRole] = useState("");
  const { token } = useAuth();

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const res = await axios.get("/api/jd/search", {
        params: {
          search_text: searchTerm || undefined,
          location: location || undefined,
          min_salary: minSalary || undefined,
          role: role || undefined
        },
        headers: { "Authorization": `Bearer ${token}` }
      });
      setJobs(res.data);
    } catch (err) {
      console.error("Lỗi tìm kiếm jobs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchJobs();
  };

  return (
    <div className={styles.pageRoot}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Khám phá Cơ hội</h1>
          <p className={styles.subtitle}>Tìm kiếm và phân tích độ phù hợp với các vị trí hàng đầu trên quy mô toàn cầu.</p>
        </div>
        
        <form onSubmit={handleSearch} className={styles.searchForm}>
            <div className={styles.searchContainer}>
                <div className={styles.inputWrapper}>
                    <Search size={18} className={styles.inputIcon} />
                    <input 
                        type="text"
                        placeholder="Từ khóa (Vị trí, Công ty...)"
                        className={styles.input}
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
                <div className={styles.inputWrapper}>
                    <MapPin size={18} className={styles.inputIcon} />
                    <input 
                        type="text"
                        placeholder="Địa điểm"
                        className={styles.input}
                        value={location}
                        onChange={(e) => setLocation(e.target.value)}
                    />
                </div>
                <div className={styles.inputWrapper}>
                    <Briefcase size={18} className={styles.inputIcon} />
                    <input 
                        type="text"
                        placeholder="Lương tối thiểu"
                        className={styles.input}
                        value={minSalary}
                        onChange={(e) => setMinSalary(e.target.value)}
                    />
                </div>
                <button 
                    type="submit"
                    className={styles.searchBtn}
                >
                    TÌM KIẾM
                </button>
            </div>
        </form>
      </div>

      <AnimatePresence mode="wait">
        {loading ? (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className={styles.loadingWrapper}
          >
            <Loader2 size={40} className={cn("animate-spin", styles.loadingIcon)} />
            <p className={styles.loadingText}>Đang đồng bộ cơ sở dữ liệu...</p>
          </motion.div>
        ) : jobs.length > 0 ? (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={styles.grid}
          >
            {jobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </motion.div>
        ) : (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className={styles.emptyState}
          >
            <Info size={48} className={styles.emptyIcon} />
            <h3 className={styles.emptyTitle}>Không tìm thấy kết quả</h3>
            <p className={styles.emptySub}>Hệ thống không tìm thấy công việc phù hợp với tiêu chí của bạn.</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function JobCard({ job }: { job: Job }) {
  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className={styles.card}
    >
      <div className={styles.cardTop}>
        <div className={styles.iconBox}>
          <Briefcase size={24} />
        </div>
        <span className={cn(
          styles.statusBadge,
          job.status?.toLowerCase() === "active" ? styles.statusActive : styles.statusOther
        )}>
          {job.status || "Closed"}
        </span>
      </div>
      
      <h3 className={styles.cardTitle}>
        {job.title_raw}
      </h3>
      
      <div className={styles.cardMeta}>
        <MapPin size={14} /> 
        <span>Hybrid / Remote Enabled</span>
      </div>
      
      <Link 
        href={`/user/analysis?job_id=${job.id}`}
        className={styles.actionBtn}
      >
        Khởi chạy Phân tích
      </Link>
    </motion.div>
  );
}
